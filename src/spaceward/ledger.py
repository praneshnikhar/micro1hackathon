from __future__ import annotations

import time
from pathlib import Path

from .scout import Record
from .util import expand, read_json, write_json


def _stamp() -> str:
    return f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**6:06d}"


def save(cfg, records: list[Record], stats: dict) -> Path:
    path = cfg.manifests_dir / f"{_stamp()}.json"
    write_json(path, {"created": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                      "stats": stats,
                      "records": [r.__dict__ for r in records]})
    prune(cfg, keep=10)
    return path


def prune(cfg, keep: int = 10) -> None:
    manifests = sorted(cfg.manifests_dir.glob("*.json"))
    for old in manifests[:-keep]:
        old.unlink(missing_ok=True)


def latest(cfg) -> Path | None:
    manifests = sorted(cfg.manifests_dir.glob("*.json"))
    return manifests[-1] if manifests else None


def latest_before(cfg, exclude: Path) -> Path | None:
    manifests = sorted(p for p in cfg.manifests_dir.glob("*.json") if p != exclude)
    return manifests[-1] if manifests else None


def load(path: Path) -> list[Record]:
    data = read_json(path, {})
    return [Record(**r) for r in data.get("records", [])]


def diff(old: list[Record], new: list[Record], growth_min_bytes: int) -> dict:
    old_map = {r.path: r for r in old if r.complete}
    new_map = {r.path: r for r in new if r.complete}
    added = [r for p, r in new_map.items()
             if p not in old_map and r.size >= growth_min_bytes
             and not any(o.path.startswith(p.rstrip("/") + "/") and not o.complete for o in old)]
    grown = []
    for p, r in new_map.items():
        prev = old_map.get(p)
        if prev and r.size - prev.size >= growth_min_bytes:
            grown.append({"path": p, "delta": r.size - prev.size,
                          "was": prev.size, "now": r.size})
    removed = [r.path for p, r in old_map.items() if p not in new_map and r.size >= growth_min_bytes]
    added.sort(key=lambda r: r.size, reverse=True)
    grown.sort(key=lambda g: g["delta"], reverse=True)
    return {"added": added, "grown": grown, "removed": removed,
            "compared": min(len(old_map), len(new_map))}
