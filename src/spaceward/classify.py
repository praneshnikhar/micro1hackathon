from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from .knowledge import CAUTION, FORBIDDEN, Hit, SAFE, TIER_RANK, classify_path, process_name_for
from .llm import get_provider
from .scout import Record
from .util import fingerprint


@dataclass
class Candidate:
    cid: str
    path: str
    size: int
    tier: str
    rule_key: str
    regen: str
    evidence: list[str] = field(default_factory=list)
    action: str = "quarantine"

    @property
    def fingerprint(self) -> dict:
        try:
            return fingerprint(Path(self.path))
        except OSError:
            return {}


def _mtime_age_days(mtime: float) -> int:
    import time
    return int((time.time() - mtime) / 86400)


_GIT_CACHE: dict[str, int | None] = {}


def _git_last_commit_age(path: str) -> int | None:
    p = Path(path)
    for parent in [p, *p.parents]:
        if (parent / ".git").exists():
            key = str(parent)
            if key in _GIT_CACHE:
                return _GIT_CACHE[key]
            try:
                out = subprocess.run(
                    ["git", "-C", key, "log", "-1", "--format=%ct"],
                    capture_output=True, text=True, timeout=5,
                )
                if out.returncode == 0 and out.stdout.strip():
                    import time
                    age = int((time.time() - int(out.stdout.strip())) / 86400)
                else:
                    age = None
            except (OSError, subprocess.TimeoutExpired):
                age = None
            _GIT_CACHE[key] = age
            return age
    return None


def _process_running(name: str) -> bool:
    try:
        out = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True, timeout=10)
        return out.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


PROJECT_SCOPED_KEYS = {"node_modules", "venv", ".venv", "target", "Pods",
                       "build-output", ".next", ".nuxt", ".svelte-kit"}
ACTIVE_PROJECT_DAYS = 7


def _build_evidence(rec: Record, hit: Hit) -> list[str]:
    ev = [f"size={rec.size} bytes",
          f"last_modified={_mtime_age_days(rec.mtime)}d ago"]
    if hit.regen:
        ev.append(f"regeneration={hit.regen}")
    if hit.note:
        ev.append(f"note={hit.note}")
    proc = process_name_for(hit.rule_key)
    if proc:
        running = _process_running(proc)
        ev.append(f"process={proc} {'RUNNING' if running else 'not running'}")
    return ev


def select_candidates(records: list[Record], changed: dict, cfg) -> list[Record]:
    min_size = cfg.candidate_min_size_mb * 1024 * 1024
    selected: dict[str, Record] = {}
    for r in records:
        if r.complete and r.size >= min_size:
            selected[r.path] = r
    for r in changed.get("added", []):
        if r.size >= min_size:
            selected[r.path] = r
    for g in changed.get("grown", []):
        was_landmark = g["path"] in selected and selected[g["path"]].landmark
        selected[g["path"]] = Record(path=g["path"], size=g["now"], mtime=0.0,
                                     complete=True, landmark=was_landmark)

    landmarks = [p for p, r in selected.items() if r.landmark]
    for lm in landmarks:
        for p in [p for p in selected if p.startswith(lm.rstrip("/") + "/")]:
            del selected[p]

    structural = set()
    paths = list(selected)
    for p in paths:
        if any(q != p and q.startswith(p.rstrip("/") + "/") for q in paths):
            structural.add(p)
    for p in structural:
        del selected[p]

    return sorted(selected.values(), key=lambda r: r.size, reverse=True)[:60]


def classify(records: list[Record], changed: dict, cfg,
             provider=None) -> tuple[list[Candidate], list[Candidate]]:
    provider = provider or get_provider(cfg.provider)
    home = str(Path.home())
    candidates: list[Candidate] = []
    refused: list[Candidate] = []
    from .memory import Memory
    memory = Memory(cfg.state_dir)

    for i, rec in enumerate(select_candidates(records, changed or {}, cfg), 1):
        p = Path(rec.path)
        is_dir = p.is_dir()
        hit = classify_path(rec.path, p.name, is_dir, home)
        if hit is None:
            tier, reason = provider.classify_unknown(rec.path, rec.size, [])
            hit = Hit(tier, "unknown", note=reason)
        if hit.tier == SAFE and hit.rule_key in PROJECT_SCOPED_KEYS:
            age = _git_last_commit_age(rec.path)
            if age is not None:
                hit.note = f"project_git_activity={age}d ago"
                if age <= ACTIVE_PROJECT_DAYS:
                    hit.tier = CAUTION
                    hit.note += f"; active project (commit {age}d ago), downgrade for workflow safety"
        ev = _build_evidence(rec, hit)
        if memory.should_skip(rec.path, hit.rule_key):
            ev.append("memory=previously rejected; skipped")
            continue
        cand = Candidate(
            cid=f"cand-{i:03d}",
            path=rec.path,
            size=rec.size,
            tier=hit.tier,
            rule_key=hit.rule_key,
            regen=hit.regen,
            evidence=ev,
        )
        if hit.tier == FORBIDDEN:
            cand.action = "refuse"
            refused.append(cand)
        else:
            candidates.append(cand)

    candidates.sort(key=lambda c: (TIER_RANK[c.tier], -c.size))
    for n, c in enumerate(candidates, 1):
        c.cid = f"cand-{n:03d}"
    for n, c in enumerate(refused, 1):
        c.cid = f"ref-{n:03d}"
    return candidates, refused
