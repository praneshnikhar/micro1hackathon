# Trajectories

Representative agent trajectories, per the submission requirements. Every file is real output from a real run — no hand-edited steps.

## `eval-run.jsonl` — full pipeline, phase by phase

From the evaluation run (12-case fixture). Read top to bottom; each line is one JSON event.

| Step | What to look for |
|---|---|
| `trigger` | free-space check: 2.6% vs 10% threshold — the preventive trigger, not a human remembering |
| `scout` | manifest stats: 12 artifacts walked, skipped counts honest |
| `differential` | `grown: 4, added: 1` — the ledger catches the +40 MB build cache **before** any size ranking sees it as special |
| `plan` | every candidate carries tier + evidence lines: `regeneration=…`, `project_git_activity=0d ago`, `process=…` |
| `gate` | approved candidate IDs — the human decision boundary |
| `execute` | quarantine moves with fingerprints; skipped items carry reasons |
| `verify` | per-action checks (path removed, quarantine copy exists, source intact) + df delta |
| `report` | sign-off report path — the artifact a person signs their name to |

## `interactive-gate.jsonl` + `interactive-gate-session.log` — a real human checkpoint

Captured over a pty with `expect` (session log is the raw terminal transcript):

1. The SAFE batch prompt lists 4 items with regeneration costs → human approves `y`
2. Four CAUTION items presented one by one with full evidence (offline music cache, active project's node_modules with git evidence, two app-support databases) → human rejects each `n`
3. Execution proceeds on approved IDs only; verification 4/4 passed

Also in this session's history: a **no-TTY refusal** (`refusing to execute`) — the gate refuses to act without a human present, which is the ground-rule-04 safety property working as intended.

## What the retry/feedback loop looks like

The eval harness itself drove retries: the first differential returned `grown: 0` because two manifests landed in the same second (one overwrote the other). The trajectory showed `differential: {against: null}` on a run that *had* a predecessor — that contradiction is what led to the sub-second-stamp fix now in `ledger.py`. See CHANGELOG v0.3/v0.6.

## Reproducing trajectories

```bash
uv run python eval/run_eval.py     # writes a fresh run to ~/.spaceward-state equivalent via env
```
Set `SPACEWARD_STATE_DIR=/tmp/my-state` to isolate; trajectories land in `$SPACEWARD_STATE_DIR/trajectories/`.
