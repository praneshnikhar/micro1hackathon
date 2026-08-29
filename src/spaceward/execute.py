from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .classify import Candidate
from .util import write_json


@dataclass
class ExecutedAction:
    cid: str
    original_path: str
    quarantine_path: str
    size: int
    tier: str
    note: str = ""


def quarantine_candidate(cand: Candidate, cfg) -> ExecutedAction | None:
    src = Path(cand.path)
    if not src.exists():
        return None
    fp_now = cand.fingerprint
    fp_plan = getattr(cand, "_plan_fingerprint", None)
    if fp_plan and fp_now and fp_now != fp_plan:
        return ExecutedAction(cid=cand.cid, original_path=cand.path, quarantine_path="",
                              size=cand.size, tier=cand.tier,
                              note="SKIPPED: path changed since plan (fingerprint mismatch)")
    dest_dir = cfg.quarantine_dir / cand.cid
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    try:
        shutil.move(str(src), str(dest))
    except (shutil.Error, OSError) as exc:
        return ExecutedAction(cid=cand.cid, original_path=cand.path, quarantine_path="",
                              size=cand.size, tier=cand.tier, note=f"FAILED: {exc}")
    write_json(dest_dir / "meta.json", {
        "cid": cand.cid,
        "original_path": cand.path,
        "size": cand.size,
        "tier": cand.tier,
        "moved_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
    })
    log_action(cfg, {"event": "quarantined", **asdict(_action(cand, dest))})
    return _action(cand, dest)


def _action(cand: Candidate, dest: Path) -> ExecutedAction:
    return ExecutedAction(cid=cand.cid, original_path=cand.path,
                          quarantine_path=str(dest), size=cand.size, tier=cand.tier)


def restore(cid: str, cfg) -> str:
    qdir = cfg.quarantine_dir / cid
    meta_path = qdir / "meta.json"
    if not meta_path.exists():
        return f"no quarantined item with id {cid}"
    meta = json.loads(meta_path.read_text())
    original = Path(meta["original_path"])
    src = qdir / original.name
    if not src.exists():
        return f"quarantined data for {cid} is missing"
    original.parent.mkdir(parents=True, exist_ok=True)
    if original.exists():
        return f"cannot restore {cid}: original path already exists"
    shutil.move(str(src), str(original))
    shutil.rmtree(qdir, ignore_errors=True)
    log_action(cfg, {"event": "restored", "cid": cid, "path": str(original)})
    return f"restored {cid} -> {original}"


def log_action(cfg, event: dict) -> None:
    log_path = cfg.state_dir / "actions.jsonl"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a") as fh:
        fh.write(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                             **event}, default=str) + "\n")
