from __future__ import annotations

from dataclasses import dataclass, field

from .classify import Candidate
from .util import fmt_bytes


@dataclass
class Plan:
    candidates: list[Candidate]
    refused: list[Candidate]
    context: dict = field(default_factory=dict)

    def total_by_tier(self) -> dict:
        totals: dict[str, int] = {}
        for c in self.candidates:
            totals[c.tier] = totals.get(c.tier, 0) + c.size
        return totals

    def render(self) -> str:
        lines = []
        ctx = self.context
        if ctx:
            if ctx.get("changed"):
                lines.append("what changed since last scan:")
                for g in ctx["changed"].get("grown", [])[:5]:
                    lines.append(f"  GROWN  +{fmt_bytes(g['delta'])}  {g['path']}")
                for r in ctx["changed"].get("added", [])[:5]:
                    lines.append(f"  NEW    {fmt_bytes(r.size)}    {r.path}")
                if not ctx["changed"]["grown"] and not ctx["changed"]["added"]:
                    lines.append("  nothing significant changed; ranked by size")
            if ctx.get("free_pct") is not None:
                lines.append(f"free space: {ctx['free_pct']:.1f}% (threshold {ctx['threshold_pct']}%)")
        if self.refused:
            lines.append(f"refused ({len(self.refused)}): never proposed for deletion")
            for c in self.refused:
                lines.append(f"  {c.cid}  {fmt_bytes(c.size)}  {c.path}")
                for e in c.evidence:
                    lines.append(f"         {e}")
        if not self.candidates:
            lines.append("no actionable candidates")
            return "\n".join(lines)
        lines.append(f"proposal ({len(self.candidates)} candidates):")
        for c in self.candidates:
            lines.append(f"  {c.cid}  [{c.tier:^7}] {fmt_bytes(c.size):>12}  {c.path}")
            for e in c.evidence:
                lines.append(f"           {e}")
        return "\n".join(lines)
