from __future__ import annotations

import json
import sys
from pathlib import Path

from .classify import Candidate
from .memory import Memory
from .util import fmt_bytes


def _record_decisions(cands: list[Candidate], approved: set[str], memory: Memory) -> None:
    for c in cands:
        memory.record(c.path, c.rule_key, "accepted" if c.cid in approved else "rejected")
    memory.save()


def gate(plan, cfg, yes_file: str | None, execute: bool) -> set[str]:
    if not execute:
        return set()

    if yes_file:
        data = json.loads(Path(yes_file).read_text())
        approved_raw = data.get("approve", []) if isinstance(data, dict) else data
        if approved_raw == "all":
            approved = {c.cid for c in plan.candidates}
        else:
            known = {c.cid for c in plan.candidates}
            approved = {cid for cid in approved_raw if cid in known}
            unknown = set(approved_raw) - known
            if unknown:
                print(f"warning: ignoring unknown candidate ids: {sorted(unknown)}", file=sys.stderr)
        _record_decisions(plan.candidates, approved, Memory(cfg.state_dir))
        return approved

    if not sys.stdin.isatty():
        raise SystemExit(
            "refusing to execute: no TTY for approval and no --yes-file provided\n"
            "pass --yes-file with {\"approve\": [\"cand-001\", ...]} or {\"approve\": \"all\"}"
        )

    approved: set[str] = set()
    by_tier: dict[str, list[Candidate]] = {}
    for c in plan.candidates:
        by_tier.setdefault(c.tier, []).append(c)

    safe = by_tier.get("SAFE", [])
    if safe:
        total = sum(c.size for c in safe)
        print(f"\nSAFE tier — regenerable artifacts ({len(safe)} items, {fmt_bytes(total)}):")
        for c in safe:
            print(f"  {c.cid}  {fmt_bytes(c.size):>12}  {c.path}")
            print(f"         regen: {c.regen}")
        ans = input(f"approve ALL {len(safe)} SAFE items? [y/N] ").strip().lower()
        if ans == "y":
            approved |= {c.cid for c in safe}
        elif ans == "n" and len(by_tier) == 1:
            pass

    for c in by_tier.get("CAUTION", []):
        print(f"\nCAUTION — {c.cid}  {fmt_bytes(c.size)}  {c.path}")
        for e in c.evidence:
            print(f"   {e}")
        ans = input("approve? [y/N/a=approve all remaining caution] ").strip().lower()
        if ans == "a":
            approved |= {x.cid for x in by_tier.get("CAUTION", [])}
            break
        if ans == "y":
            approved.add(c.cid)

    _record_decisions(plan.candidates, approved, Memory(cfg.state_dir))
    return approved
