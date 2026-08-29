# Spaceward — 5-minute video script

Format: screen recording, terminal-first. One take per section; cut between sections.

## 0:00–0:45 — The problem (before)

- Show the real morning: `df -h` → 3.2 GB free of 228 GB (99% full)
- Narrate: "Every dev tool caches and never deletes. Disk fills gradually, then all at once — usually mid-build with ENOSPC. This morning it was my machine."
- Show the manual process: scrolling `du -sh */`, reading paths, hesitating over `Caches/com.spotify.client` — "is this safe? It says cache, but it might hold offline music"
- Punchline: "20 minutes later I'd freed 4.5GB, one approval at a time. That session is the baseline — and it's the product brief."

## 0:45–1:30 — The baseline systems

- Show `baselines/b2_naive/naive.py`: 20 lines, deletes every node_modules, every file >30MB
- Run it on the fixture; show the 6 broken things (offline music gone, active project's deps gone, credentials deleted, Docker VM deleted)
- Narrate: "Same recall as my final agent. Six broken things. Recall was never the hard problem — earning the right to delete is."

## 1:30–3:00 — One realistic execution, start to finish

- `uv run spaceward run --simulate-threshold --execute --roots fixture` (recorded via expect/pty so the gate is real)
- Walk the plan on screen:
  - "What changed since last scan: a build cache grew 40MB overnight — that's the differential ledger; scanners can't answer this question"
  - "Two paths refused outright: Docker.raw would destroy all images; a .pem is credentials. Never proposed, with reasons."
  - "This node_modules says CAUTION — why? One git call: commit 0 days ago, active project. Downgraded for workflow safety."
  - Approve SAFE batch `y`, reject a CAUTION `n`
- Verification: 4/4 checks pass; sign-off report on screen: paths, evidence, df delta, restore command

## 3:00–3:45 — The comparison + changelog

- `results/comparison.md` on screen: 194MB / 0 failures / 2 min vs baselines
- Changelog highlights: naive script → knowledge tiers → differential ledger → gate+quarantine → git downgrade
- "The single biggest contributor: context evidence. One git call took false positives from 1 to 0."

## 3:45–4:30 — One removed experiment

- "I first built LLM-first classification: every path through the model. It 401'd mid-eval and made results nondeterministic. Removed: classification is now deterministic; the LLM is optional, only for unknown paths. The lesson: agents win here by being auditable, not bigger calculators."
- Optionally show `--provider anthropic` classifying an unknown path live

## 4:30–5:00 — Reproduce it

- Clean terminal: `git clone … && uv sync && uv run python eval/run_eval.py` → comparison table regenerates
- Close on the hot take: "Everyone builds scanners because scanning is measurable. Nobody builds guardians because prevention is invisible. Spaceward is the guardian."

## Recording notes

- Record at 2560×1440, terminal font ≥ 20pt, dark theme
- Pre-stage: `tmux` panes for df/plan/report so cuts are instant
- Keep cursor visible during gate interaction — the human moment is the product
