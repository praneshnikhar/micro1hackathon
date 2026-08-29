from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval import fixtures
from eval.harness import ALL_SYSTEMS, run_system

RESULTS = Path(__file__).resolve().parent.parent / "results"


def fmt_mb(n: float) -> str:
    return f"{n / 1024 / 1024:.0f} MB"


def main() -> int:
    RESULTS.mkdir(exist_ok=True)
    template = fixtures.build(RESULTS.parent and Path("/tmp/spaceward-eval/template"))
    results = [run_system(name, template) for name in ALL_SYSTEMS]
    (RESULTS / "results.json").write_text(json.dumps(results, indent=2))

    by = {r["system"]: r for r in results}
    lines = [
        f"# Spaceward evaluation — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Fixture: {len(fixtures.ARTIFACTS)} artifacts, "
        f"{fmt_mb(sum(a.size_mb for a in fixtures.ARTIFACTS if a.verdict == 'safe') * 1024 * 1024)} safe / "
        f"{fmt_mb(sum(a.size_mb for a in fixtures.ARTIFACTS if a.verdict == 'keep') * 1024 * 1024)} protected. "
        "Same state for every system; one trap case per failure mode.",
        "",
        "## Comparison (brief format)",
        "",
        "| Metric | B1 manual | B2 naive script | B3 basic agent | Spaceward |",
        "|---|---|---|---|---|",
    ]

    def row(label, key, fmt):
        cells = []
        for name in ALL_SYSTEMS:
            v = by[name].get(key)
            cells.append(fmt(v) if v is not None else "-")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")

    row("Primary: safe bytes reclaimed (of total safe)", "reclaimed_bytes", fmt_mb)
    row("Primary: integrity failures (must be 0)", "integrity_failures", str)
    row("Recall of safe bytes", "recall", lambda v: f"{v * 100:.0f}%")
    row("Human time per task", "human_time", str)
    row("Cost per task", "cost", str)
    lines.append("")
    lines.append("## Per-case breakdown")
    lines.append("")
    truth = fixtures.ARTIFACTS
    lines.append("| Case | Verdict | B1 | B2 | B3 | Spaceward |")
    lines.append("|---|---|---|---|---|---|")

    def deleted_case(r, rel):
        if any(fp["path"] == rel for fp in r.get("false_positives", [])):
            return "DELETED (wrong)"
        if rel in r.get("missed_safe_relpaths", []):
            return "missed"
        truth_entry = {a.relpath: a for a in truth}[rel]
        return "kept" if truth_entry.verdict == "keep" else "DELETED"

    for art in truth:
        cells = [deleted_case(by[name], art.relpath) for name in ALL_SYSTEMS]
        lines.append(f"| {art.relpath} | {art.verdict} | " + " | ".join(cells) + " |")

    sw = by["spaceward"]
    diff = sw.get("differential") or {}
    lines += ["", "## Spaceward differential evidence",
              "",
              f"run rc={sw.get('rc')}, grown={diff.get('grown', 0)}, "
              f"added={diff.get('added', 0)}"]
    (RESULTS / "comparison.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
