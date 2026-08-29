from __future__ import annotations

import time
from pathlib import Path

from .execute import ExecutedAction
from .plan import Plan
from .util import fmt_bytes, write_json


def build_report(cfg, plan: Plan, executed: list[ExecutedAction], results: list[dict],
                 disk: dict, approved: set[str], stats: dict, changed: dict) -> Path:
    ts = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())
    lines = [f"# Spaceward cleanup report — {ts}", ""]
    lines.append(f"free space: {fmt_bytes(disk['free_before'])} -> {fmt_bytes(disk['free_after'])} "
                 f"(df recovered {fmt_bytes(disk['recovered'])}; APFS may reclaim asynchronously)")
    lines.append(f"quarantined (planned): {fmt_bytes(disk.get('quarantined_bytes', 0))}")
    lines.append(f"scan: {stats}")
    lines.append("")

    if changed and (changed.get("grown") or changed.get("added")):
        lines.append("## What changed since last scan")
        for g in changed.get("grown", []):
            lines.append(f"- GROWN +{fmt_bytes(g['delta'])}: {g['path']}")
        for r in changed.get("added", []):
            lines.append(f"- NEW {fmt_bytes(r.size)}: {r.path}")
        lines.append("")

    lines.append("## Refused (never proposed)")
    if plan.refused:
        for c in plan.refused:
            lines.append(f"- `{c.cid}` {fmt_bytes(c.size)} `{c.path}` — {c.rule_key}")
    else:
        lines.append("- none")
    lines.append("")

    lines.append("## Approved and executed")
    if executed:
        for a in executed:
            lines.append(f"- `{a.cid}` {fmt_bytes(a.size)} `{a.original_path}` -> `{a.quarantine_path}`"
                         + (f" ({a.note})" if a.note else ""))
    else:
        lines.append("- nothing executed")
    lines.append("")

    lines.append("## Verification")
    if results:
        for r in results:
            status = "PASS" if r["ok"] else "FAIL"
            lines.append(f"- `{r['cid']}` {status}")
            for c in r["checks"]:
                lines.append(f"  - {'ok' if c.get('ok') else 'FAILED'}: {c['check']}")
    else:
        lines.append("- no actions to verify")
    lines.append("")

    lines.append("## Undo")
    lines.append("Every executed item is recoverable: `spaceward restore <cid>`")
    lines.append("Restore all, then delete the quarantine dir when satisfied.")

    path = cfg.reports_dir / f"{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 10**6:06d}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    return path
