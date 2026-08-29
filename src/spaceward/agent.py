from __future__ import annotations

import json
import time

from .classify import classify
from .execute import quarantine_candidate
from .gate import gate
from .ledger import diff, latest_before, load, save
from .plan import Plan
from .report import build_report
from .scout import build_manifest, disk_usage
from .util import fmt_bytes
from .verify import disk_delta, verify_actions


class Trajectory:
    def __init__(self, cfg, run_id: str):
        self.path = cfg.trajectories_dir / f"run-{run_id}.jsonl"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, step: str, data) -> None:
        event = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime()),
                 "step": step, "data": data}
        with self.path.open("a") as fh:
            fh.write(json.dumps(event, default=str) + "\n")


def run_pipeline(cfg, simulate_threshold: bool = False, execute: bool = False,
                 dry_run: bool = False, yes_file: str | None = None,
                 roots: list[str] | None = None) -> int:
    run_id = f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**6:06d}"
    traj = Trajectory(cfg, run_id)

    total, free = disk_usage("/")
    free_pct = free / total * 100
    traj.log("trigger", {"free_bytes": free, "free_pct": round(free_pct, 2),
                         "threshold_pct": cfg.threshold_pct, "simulated": simulate_threshold})

    if free_pct >= cfg.threshold_pct and not simulate_threshold:
        print(f"disk healthy: {free_pct:.1f}% free (threshold {cfg.threshold_pct}%). nothing to do.")
        print(f"force a run with --simulate-threshold")
        traj.log("outcome", {"result": "healthy"})
        return 0

    print(f"disk low: {free_pct:.1f}% free — investigating what changed")
    before = (total, free)

    records, stats = build_manifest(roots or cfg.roots, cfg)
    manifest_path = save(cfg, records, stats)
    traj.log("scout", {"manifest": str(manifest_path), "stats": stats})

    changed: dict = {}
    prev = latest_before(cfg, manifest_path)
    if prev:
        changed = diff(load(prev), records, cfg.growth_min_mb * 1024 * 1024)
        traj.log("differential", {"against": str(prev),
                                  "grown": len(changed["grown"]),
                                  "added": len(changed["added"])})
    else:
        traj.log("differential", {"against": None, "note": "first run; no baseline manifest"})

    candidates, refused = classify(records, changed, cfg)
    plan = Plan(candidates=candidates, refused=refused,
                context={"changed": changed, "free_pct": free_pct,
                         "threshold_pct": cfg.threshold_pct})
    traj.log("plan", {"candidates": [c.__dict__ for c in plan.candidates],
                      "refused": [c.__dict__ for c in plan.refused]})

    print()
    print(plan.render())
    print()

    if dry_run or not execute:
        print("plan only — re-run with --execute (and an approval gate) to act")
        traj.log("outcome", {"result": "plan_only"})
        return 0

    approved = gate(plan, cfg, yes_file, execute)
    traj.log("gate", {"approved": sorted(approved)})
    if not approved:
        print("nothing approved; nothing deleted")
        traj.log("outcome", {"result": "no_approval"})
        return 0

    approved_cands = [c for c in plan.candidates if c.cid in approved]
    for c in approved_cands:
        c._plan_fingerprint = c.fingerprint
    executed = []
    for c in approved_cands:
        action = quarantine_candidate(c, cfg)
        if action:
            executed.append(action)
            status = action.note or f"quarantined -> {action.quarantine_path}"
            print(f"  {c.cid}: {status}")
    traj.log("execute", {"executed": [a.__dict__ for a in executed]})

    results = verify_actions(executed)
    disk = disk_delta(before)
    disk["quarantined_bytes"] = sum(a.size for a in executed
                                    if a.quarantine_path and not a.note)
    traj.log("verify", {"results": results, "disk": disk})

    report_path = build_report(cfg, plan, executed, results, disk, approved, stats, changed)
    traj.log("report", {"path": str(report_path)})

    print()
    print(f"quarantined: {fmt_bytes(disk['quarantined_bytes'])} (planned)")
    print(f"df recovered: {fmt_bytes(disk['recovered'])} — APFS may reclaim asynchronously")
    failed = [r for r in results if not r["ok"]]
    print(f"verification: {len(results) - len(failed)}/{len(results)} passed")
    print(f"report: {report_path}")
    traj.log("outcome", {"result": "executed", "recovered_bytes": disk["recovered"],
                         "verification_failures": len(failed)})
    return 0
