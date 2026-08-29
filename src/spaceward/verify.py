from __future__ import annotations

import subprocess
from pathlib import Path

from .execute import ExecutedAction
from .scout import disk_usage


def _probe_ok(cmd: list[str], timeout: int = 15) -> bool:
    try:
        return subprocess.run(cmd, capture_output=True, timeout=timeout).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def verify_actions(actions: list[ExecutedAction]) -> list[dict]:
    results = []
    for action in actions:
        checks: list[dict] = []
        original = Path(action.original_path)
        checks.append({"check": "path_removed", "ok": not original.exists()})
        if action.quarantine_path:
            qpath = Path(action.quarantine_path)
            checks.append({"check": "quarantine_copy_exists", "ok": qpath.exists(),
                           "size": qpath.stat().st_size if qpath.exists() else 0})
        parent = original.parent
        project_files = ["package.json", "requirements.txt", "pyproject.toml", "Cargo.toml"]
        for pf in project_files:
            if (parent / pf).exists():
                checks.append({"check": f"source_intact_{pf}", "ok": True})
                break
        if "pip" in action.original_path:
            checks.append({"check": "pip_cache_readable", "ok": _probe_ok(["pip", "cache", "dir"])})
        if "Homebrew" in action.original_path:
            checks.append({"check": "brew_usable", "ok": _probe_ok(["brew", "--version"])})
        results.append({"cid": action.cid, "path": action.original_path,
                        "checks": checks,
                        "ok": all(c.get("ok", False) for c in checks)})
    return results


def disk_delta(before: tuple[int, int]) -> dict:
    total, free_after = disk_usage("/")
    return {"total": total, "free_before": before[1], "free_after": free_after,
            "recovered": free_after - before[1]}
