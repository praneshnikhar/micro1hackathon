from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

BIG_FILE_MB = 30
LANDMARK_NAMES = {"node_modules", ".next", ".turbo", "build"}


def naive_clean(root: Path, trash: Path) -> list[str]:
    trash.mkdir(parents=True, exist_ok=True)
    deleted = []
    for p in list(root.rglob("*")):
        if not p.exists() or p.is_symlink():
            continue
        rel = str(p.relative_to(root))
        if rel.startswith("ground_truth"):
            continue
        try:
            if p.is_dir() and p.name in LANDMARK_NAMES:
                dest = trash / f"d-{abs(hash(rel))}"
                shutil.move(str(p), str(dest))
                deleted.append(str(p))
            elif p.is_file() and p.stat().st_size >= BIG_FILE_MB * 1024 * 1024:
                dest = trash / f"f-{abs(hash(rel))}"
                shutil.move(str(p), str(dest))
                deleted.append(str(p))
        except (OSError, shutil.Error):
            continue
    return deleted


def main() -> int:
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    t0 = time.monotonic()
    trash = root.parent / f"{root.name}-trash-{int(time.time())}"
    deleted = naive_clean(root, trash)
    wall = time.monotonic() - t0
    out.write_text(json.dumps({"deleted": deleted, "wall_seconds": wall}, indent=2))
    print(f"b2: {len(deleted)} deletions in {wall:.1f}s (naive size-based script)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
