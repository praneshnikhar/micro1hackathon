from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval import fixtures
from eval.scoring import score

REPO = Path(__file__).resolve().parent.parent
EVAL_ROOT = Path("/tmp/spaceward-eval")

HUMAN_TIME = {
    "b1_manual": "20 min (real session, 2026-08-29)",
    "b2_naive": "2 min (author once) + 1 s per run",
    "b3_basic_agent": "3 min",
    "spaceward": "2 min (review plan, approve tiers)",
}
COST = {
    "b1_manual": "$0",
    "b2_naive": "$0",
    "b3_basic_agent": "$0 (proxy) / ~$0.01 (llm mode)",
    "spaceward": "$0 (heuristic) / ~$0.01 (llm mode)",
}


def _fresh_run_dir(name: str, template: Path) -> Path:
    run_root = EVAL_ROOT / name
    if run_root.exists():
        shutil.rmtree(run_root)
    shutil.copytree(template, run_root, ignore=shutil.ignore_patterns("ground_truth.json"))
    return run_root


def _run_subprocess(name: str, script: Path, run_root: Path) -> tuple[list[str], float]:
    out = EVAL_ROOT / f"{name}-deletions.json"
    proc = subprocess.run([sys.executable, str(script), str(run_root), str(out)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"{name} failed:\n{proc.stdout}\n{proc.stderr}")
    print(proc.stdout.strip())
    data = json.loads(out.read_text())
    return data["deleted"], data["wall_seconds"]


def _run_spaceward(run_root: Path) -> tuple[list[str], float, dict]:
    state = EVAL_ROOT / "spaceward-state"
    if state.exists():
        shutil.rmtree(state)
    os.environ["SPACEWARD_STATE_DIR"] = str(state)
    for mod in [m for m in list(sys.modules) if m.startswith("spaceward")]:
        del sys.modules[mod]
    from spaceward.agent import run_pipeline
    from spaceward.config import Config
    from spaceward.ledger import save
    from spaceward.scout import build_manifest

    cfg = Config.load()
    yes = state / "yes.json"
    yes.parent.mkdir(parents=True, exist_ok=True)
    yes.write_text('{"approve_tiers": ["SAFE"]}')

    t0 = time.monotonic()
    records, _ = build_manifest([str(run_root)], cfg)
    save(cfg, records, {"note": "pre-growth baseline"})
    fixtures.apply_growth(run_root)
    rc = run_pipeline(cfg, simulate_threshold=True, execute=True,
                      yes_file=str(yes), roots=[str(run_root)])
    wall = time.monotonic() - t0

    deletions = []
    actions = state / "actions.jsonl"
    if actions.exists():
        for line in actions.read_text().splitlines():
            event = json.loads(line)
            if event.get("event") == "quarantined":
                deletions.append(event["original_path"])
    traj_files = sorted((state / "trajectories").glob("*.jsonl"))
    differential = {}
    if traj_files:
        for line in traj_files[-1].read_text().splitlines():
            event = json.loads(line)
            if event["step"] == "differential":
                differential = event["data"]
    return deletions, wall, {"rc": rc, "differential": differential}


def run_system(name: str, template: Path) -> dict:
    run_root = _fresh_run_dir(name, template)
    if name == "b1_manual":
        deleted, wall = _run_subprocess(name, REPO / "baselines/b1_manual/careful_human.py", run_root)
        extra = {}
    elif name == "b2_naive":
        deleted, wall = _run_subprocess(name, REPO / "baselines/b2_naive/naive.py", run_root)
        extra = {}
    elif name == "b3_basic_agent":
        deleted, wall = _run_subprocess(name, REPO / "baselines/b3_basic_agent/agent.py", run_root)
        extra = {}
    elif name == "spaceward":
        deleted, wall, extra = _run_spaceward(run_root)
    else:
        raise ValueError(name)
    return score(template / "ground_truth.json", run_root, deleted, wall,
                 {"system": name, "human_time": HUMAN_TIME[name], "cost": COST[name],
                  "deleted_count": len(deleted), **extra})


ALL_SYSTEMS = ["b1_manual", "b2_naive", "b3_basic_agent", "spaceward"]
