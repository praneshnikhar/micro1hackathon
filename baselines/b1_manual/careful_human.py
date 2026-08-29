from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

TOP_INSPECT = 10
KNOWN_COMMANDS = ["Library/Caches/pip"]


def _git_age(project: Path) -> int | None:
    if not (project / ".git").exists():
        return None
    try:
        out = subprocess.run(
            ["git", "-C", str(project), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return int(time.time() - int(out.stdout.strip())) // 86400
    except (OSError, subprocess.TimeoutExpired):
        return None
    return None


def _du_candidates(root: Path, floor_mb: float = 25.0) -> list[tuple[int, Path]]:
    entries = []
    floor = floor_mb * 1024 * 1024
    for p in root.rglob("*"):
        if p.is_symlink() or "ground_truth" in p.name:
            continue
        try:
            if p.is_dir():
                total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            else:
                total = p.stat().st_size
            if total >= floor:
                entries.append((total, p))
        except OSError:
            continue
    entries.sort(reverse=True)
    leafy = []
    for size, p in entries:
        sp = str(p)
        if any(str(q).startswith(sp.rstrip("/") + "/") for _, q in entries if q != p):
            continue
        leafy.append((size, p))
    return leafy


def careful_human(root: Path, trash: Path) -> list[str]:
    trash.mkdir(parents=True, exist_ok=True)
    deleted = []
    candidates = _du_candidates(root)

    for known in KNOWN_COMMANDS:
        p = root / known
        if p.exists():
            shutil.move(str(p), str(trash / p.name))
            deleted.append(str(p))

    inspected = 0
    for size, p in candidates:
        if inspected >= TOP_INSPECT:
            break
        if not p.exists():
            continue
        inspected += 1
        rel = str(p.relative_to(root))
        name = p.name
        parent_name = p.parent.name
        if parent_name == "Downloads" and name.endswith((".dmg", ".pkg", ".iso", ".tgz")):
            dest = trash / f"inst-{abs(hash(rel))}"
            shutil.move(str(p), str(dest))
            deleted.append(str(p))
        elif name in {"node_modules", ".next"}:
            project = p.parent
            age = _git_age(project)
            if age is None or age > 7:
                shutil.move(str(p), str(trash / f"nm-{abs(hash(rel))}"))
                deleted.append(str(p))
        elif "Caches/pip" in rel:
            shutil.move(str(p), str(trash / f"pip-{abs(hash(rel))}"))
            deleted.append(str(p))
        else:
            continue

    return deleted


def main() -> int:
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    t0 = time.monotonic()
    trash = root.parent / f"{root.name}-trash-{int(time.time())}"
    deleted = careful_human(root, trash)
    wall = time.monotonic() - t0
    out.write_text(json.dumps({"deleted": deleted, "wall_seconds": wall}, indent=2))
    print(f"b1: {len(deleted)} deletions in {wall:.1f}s (scripted careful-human policy)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
