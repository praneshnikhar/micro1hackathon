# Reproduction Guide

From a clean machine to the full measured result. Approximate runtime: **5 minutes total, $0** (no API key required).

## Prerequisites

- macOS or Linux
- [uv](https://docs.astral.sh/uv/) (Python 3.12 is fetched automatically)
- git
- Optional: `ANTHROPIC_API_KEY` for LLM modes (not needed for the headline result)

## Setup

```bash
git clone https://github.com/praneshnikhar/micro1hackathon.git
cd micro1hackathon
uv sync
```

Verify: `uv run spaceward --help` prints the command list.

## 1. Reproduce the headline result (eval)

```bash
uv run python eval/run_eval.py
```

What it does: builds a 12-artifact fixture (154 MB safe + 294 MB protected, including a build cache that grows +40 MB mid-eval), runs all four systems on identical state, scores every deletion against ground truth.

Expected output: `results/comparison.md` and `results/results.json`.

Expected headline (Python 3.12, heuristic provider):

| System | Safe bytes reclaimed | Integrity failures | Recall |
|---|---|---|---|
| B1 manual (scripted careful human) | 108 MB | 0 | 56% |
| B2 naive script | 194 MB | **6** | 100% |
| B3 basic agent | 144 MB | 1 | 74% |
| Spaceward | **194 MB** | **0** | **100%** |

The per-case breakdown shows exactly which traps each system hits. The six B2 failures are the story: offline-app-state, node_modules-active, credentials, gray-zone, shared-app-support, docker-vm.

Runtime: ~60–90 s. Cost: $0 (B3 and Spaceward fall back to deterministic modes without an API key).

## 2. Run the baselines individually

```bash
rm -rf /tmp/spaceward-eval && uv run python -c "import sys; sys.path.insert(0,'.'); from eval import fixtures; fixtures.build('/tmp/spaceward-eval/template')"
uv run python baselines/b1_manual/careful_human.py /tmp/b1-run /tmp/b1.json    # scripted careful human
uv run python baselines/b2_naive/naive.py /tmp/b2-run /tmp/b2.json             # blind size-greedy script
uv run python baselines/b3_basic_agent/agent.py /tmp/b3-run /tmp/b3.json       # basic agent (LLM if key set)
```

(Each expects a pre-built run dir; the harness in step 1 wires this automatically — individual runs are for inspection.)

## 3. Run Spaceward

Plan only (never touches anything):

```bash
uv run spaceward run --dry-run                       # your real machine
uv run spaceward run --dry-run --roots /some/dir     # scoped scan
```

Real execution requires an approval gate — pick one:

```bash
uv run spaceward run --simulate-threshold --execute --yes-file yes.json
```

with `yes.json`:

```json
{"approve_tiers": ["SAFE"]}
```

or `{"approve": ["cand-001", "cand-003"]}` for exact IDs, or `{"approve": "all"}`. Interactive approval runs when a TTY is attached (batch y/N for SAFE, per-item for CAUTION).

Everything deleted goes to `~/.spaceward/quarantine/<cid>/`. Undo anything:

```bash
uv run spaceward restore cand-001
uv run spaceward report     # print the latest sign-off report
uv run spaceward memory show
```

Watch mode (the "preventive" in guardian): `uv run spaceward watch` — polls free space, runs the loop below the threshold (default 10%).

## 4. Agent trajectories

- `trajectories/eval-run.jsonl` — the full eval execution, phase by phase (trigger → scout → differential → plan → gate → execute → verify → report)
- `trajectories/interactive-gate.jsonl` + `trajectories/interactive-gate-session.log` — a real interactive approval: 4 SAFE approved, 4 CAUTION rejected, captured over a pty with `expect`
- `trajectories/eval-run.jsonl` also shows a refusal checkpoint (no-TTY guard) and the differential event that surfaced the sudden-growth case

## Versions & environment

- Python 3.12.x (uv-managed), zero third-party runtime dependencies
- macOS 15 (developed + evaluated), Linux-compatible paths
- LLM modes: `claude-3-5-haiku-latest` via Anthropic API, used only for unknown-path classification and B3's optional mode; every headline number above is deterministic and does not depend on it

## Troubleshooting

- **Scan seems slow / partial**: the 90 s scan budget is intentional; partial subtrees are marked `complete: false` and excluded from differentials rather than guessed at. Raise `max_scan_seconds` in `~/.spaceward/config.toml`.
- **macOS permission prompts**: scanning some `~/Library` subtrees triggers TCC; grant Full Disk Access to your terminal for a full view, or scan narrower `--roots`. Skipped dirs are counted in scan stats, never silently dropped.
- **"refusing to execute"**: that is the gate doing its job. Provide a TTY or `--yes-file`.
