from __future__ import annotations

import os
import time
from dataclasses import dataclass, asdict
from pathlib import Path

from .knowledge import LANDMARK_DIRS
from .util import expand, fmt_bytes

SKIP_DIRS = {".spaceward", "quarantine", "proc", "sys", "dev"}


@dataclass
class Record:
    path: str
    size: int
    mtime: float
    complete: bool = True
    landmark: bool = False


def disk_usage(path: str = "/") -> tuple[int, int]:
    st = os.statvfs(path)
    total = st.f_blocks * st.f_frsize
    free = st.f_bavail * st.f_frsize
    return total, free


def _is_landmark(name: str) -> bool:
    return name in LANDMARK_DIRS


def _walk(root: Path, deadline: float, min_size: int, records: list[Record], stats: dict) -> tuple[int, bool]:
    total = 0
    complete = True
    try:
        entries = list(os.scandir(root))
    except (PermissionError, FileNotFoundError, NotADirectoryError):
        stats["skipped"] += 1
        return 0, True
    except OSError:
        stats["skipped"] += 1
        return 0, True

    for i, entry in enumerate(entries):
        name = entry.name
        if name.startswith(".") and name in SKIP_DIRS:
            continue
        if i % 512 == 0 and time.monotonic() > deadline:
            complete = False
            stats["deadline_hits"] += 1
            break
        try:
            if entry.is_symlink():
                continue
            if entry.is_dir(follow_symlinks=False):
                if time.monotonic() > deadline:
                    complete = False
                    stats["deadline_hits"] += 1
                    break
                sub_size, sub_complete = _walk(Path(entry.path), deadline, min_size, records, stats)
                total += sub_size
                complete = complete and sub_complete
                lm = _is_landmark(name)
                records.append(Record(
                    path=entry.path,
                    size=sub_size,
                    mtime=entry.stat(follow_symlinks=False).st_mtime,
                    complete=complete,
                    landmark=lm,
                ))
            else:
                size = entry.stat(follow_symlinks=False).st_size
                total += size
                if size >= min_size:
                    records.append(Record(path=entry.path, size=size,
                                          mtime=entry.stat(follow_symlinks=False).st_mtime,
                                          complete=complete, landmark=False))
        except OSError:
            stats["errors"] += 1
    return total, complete


def build_manifest(roots: list[str], cfg) -> tuple[list[Record], dict]:
    deadline = time.monotonic() + cfg.max_scan_seconds
    min_size = cfg.scan_min_size_mb * 1024 * 1024
    records: list[Record] = []
    stats = {"skipped": 0, "errors": 0, "deadline_hits": 0}
    started = time.monotonic()
    for raw in roots:
        root = expand(raw)
        if not root.exists():
            continue
        root_size, root_complete = _walk(root, deadline, min_size, records, stats)
        records.append(Record(path=str(root), size=root_size, mtime=root.stat().st_mtime,
                              complete=root_complete, landmark=False))
    stats["elapsed_s"] = round(time.monotonic() - started, 1)
    stats["records"] = len(records)
    root_paths = {str(expand(raw)) for raw in roots}
    root_total = sum(r.size for r in records
                     if r.complete and r.path in root_paths)
    stats["total_scanned"] = fmt_bytes(root_total)
    return records, stats


def top_records(records: list[Record], n: int = 20) -> list[Record]:
    complete = [r for r in records if r.complete]
    return sorted(complete, key=lambda r: r.size, reverse=True)[:n]


def manifest_payload(records: list[Record], stats: dict) -> dict:
    return {"created": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
            "stats": stats,
            "records": [asdict(r) for r in records]}
