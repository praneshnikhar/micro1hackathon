from __future__ import annotations

import json
import shutil
import sys
import time
from pathlib import Path

MB = 1024 * 1024

KNOWN_SAFE_NAMES = {"node_modules", ".next", ".turbo", "__pycache__"}
KNOWN_SAFE_PATHS = ["Caches/pip"]
INSTALLER_EXT = (".dmg", ".pkg", ".iso", ".tgz")
FLOOR_MB = 25.0


def _du_candidates(root: Path) -> list[tuple[int, Path]]:
    entries = []
    for p in root.rglob("*"):
        if p.is_symlink() or "ground_truth" in p.name:
            continue
        try:
            if p.is_dir():
                total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
            else:
                total = p.stat().st_size
            if total >= FLOOR_MB * MB:
                entries.append((total, p))
        except OSError:
            continue
    return sorted(entries, reverse=True)


def llm_decide(path: str, size: int) -> bool | None:
    import os
    import urllib.request
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    prompt = ("A general-purpose cleanup agent sees this path on a full disk. "
              f"Delete it? path={path} size_mb={size // MB}. "
              'Answer strict JSON {"delete": true|false, "reason": "..."}.')
    body = json.dumps({"model": "claude-3-5-haiku-latest", "max_tokens": 120,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        return bool(json.loads(data["content"][0]["text"])["delete"])
    except Exception:
        return None


def proxy_decide(rel: str, p: Path) -> bool:
    name = p.name
    if name in KNOWN_SAFE_NAMES:
        return True
    if any(seg in rel for seg in KNOWN_SAFE_PATHS):
        return True
    if p.parent.name == "Downloads" and name.endswith(INSTALLER_EXT):
        return True
    return False


def basic_agent(root: Path, trash: Path) -> tuple[list[str], bool]:
    trash.mkdir(parents=True, exist_ok=True)
    deleted = []
    used_llm = False
    for size, p in _du_candidates(root):
        rel = str(p.relative_to(root))
        if rel.startswith("ground_truth"):
            continue
        decision = llm_decide(rel, size)
        if decision is None:
            decision = proxy_decide(rel, p)
        else:
            used_llm = True
        if decision:
            try:
                shutil.move(str(p), str(trash / f"a-{abs(hash(rel))}"))
                deleted.append(str(p))
            except (OSError, shutil.Error):
                continue
    return deleted, used_llm


def main() -> int:
    root = Path(sys.argv[1])
    out = Path(sys.argv[2])
    t0 = time.monotonic()
    trash = root.parent / f"{root.name}-trash-{int(time.time())}"
    deleted, used_llm = basic_agent(root, trash)
    wall = time.monotonic() - t0
    out.write_text(json.dumps({"deleted": deleted, "wall_seconds": wall,
                               "used_llm": used_llm}, indent=2))
    mode = "llm" if used_llm else "deterministic-proxy"
    print(f"b3: {len(deleted)} deletions in {wall:.1f}s (basic agent, {mode})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
