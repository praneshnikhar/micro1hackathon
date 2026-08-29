# Spaceward — Build Plan

**What we are building:** a preventive disk-guardian agent. It watches free space, investigates *what changed* (not just what's big), classifies deletion safety with evidence, gets itemized human approval before touching anything (trash-first), then verifies apps/builds still work and produces a sign-off report.

**Why:** the micro1 Agentic Workflows Hackathon rewards a clearly-defined user, purposeful agent design, a fair measured baseline, and reproducibility. Full rationale in [DESIGN.md](DESIGN.md).

**Stack:** Python 3.12, `uv` package manager, pluggable LLM provider (Claude CLI / API; heuristic-only fallback mode for determinism). macOS first (demo env), Linux-compatible paths.

---

## Target repo layout

```
macro1/
├── pyproject.toml              # uv project, entrypoint: spaceward
├── README.md                   # user, bottleneck, value prop
├── DESIGN.md                   # architecture + rubric mapping (done)
├── plan.md                     # this file
├── CHANGELOG.md                # improvement changelog (evidence-filled)
├── REPRODUCTION.md             # clean-env guide for judges
├── src/spaceward/
│   ├── cli.py                  # spaceward run|watch|scan|restore|report
│   ├── agent.py                # agent loop: scout→classify→plan→gate→execute→verify
│   ├── llm.py                  # provider abstraction (claude-api | claude-cli | heuristic)
│   ├── scout.py                # df/du scan, snapshot manifest
│   ├── ledger.py               # manifest storage + differential ("what changed")
│   ├── knowledge.py            # dev-cache knowledge base: path → class, risk, regen cost
│   ├── classify.py             # per-candidate risk tier + evidence assembly
│   ├── plan.py                 # itemized proposal (stable candidate IDs)
│   ├── gate.py                 # human approval: batch(low) / per-ID(caution) / phrase(irreversible)
│   ├── execute.py              # path revalidation → quarantine move → action log
│   ├── verify.py               # df delta, build/app health checks, cache regen spot-checks
│   ├── memory.py               # per-machine accept/reject ledger (persistent)
│   └── report.py               # markdown sign-off report
├── baselines/
│   ├── b1_manual/README.md     # the real manual session (this morning), timed + logged
│   ├── b2_naive/clean.sh       # find+du top offenders, rm -rf known dir names
│   └── b3_basic_agent/         # one general prompt, basic tools, no gates
├── eval/
│   ├── cases.py                # 10+ cases incl. trap cases
│   ├── harness.py              # runs B1/B2/B3/spaceward on identical state, scores
│   ├── fixtures/               # seeded fake home dir (full-disk scenario w/o a full disk)
│   └── results/                # measured JSON + comparison tables
├── trajectories/               # JSONL transcripts (one per phase, one human-gate, one retry)
└── video/script.md             # 5-min video outline
```

---

## Phase 0 — Scaffold (30 min)

- [x] `uv init`, pyproject with `[project.scripts] spaceward = "spaceward.cli:main"`
- [x] git init, first commit (baseline for the changelog)
- [x] Decide LLM provider default: Claude API via env key; `--provider heuristic` runs the full pipeline with zero LLM calls (deterministic judge runs)
- [x] Config file `~/.spaceward/config.toml`: threshold %, watch interval, quarantine dir, allow/deny lists

**Done when:** `spaceward --help` works from a clean clone.

## Phase 1 — Scout + differential ledger (the core differentiator) (2–3 h)

- [x] `scout.py`: read `df` free space; walk high-yield roots (home, ~/Library, ~/coding2, common cache roots) with size caps and time budget; emit a manifest: `path, bytes, mtime, kind-guess`
- [x] `ledger.py`: store manifests as JSONL under `~/.spaceward/manifests/`; diff two manifests → *added / grown / stable* paths since last good state
- [x] Crisis framing output: "5.2GB appeared in the last 3 days across 3 paths" — the question no scanner answers
- [x] Scan is strictly read-only; heavy walk uses `os.scandir`, skip symlinks, respect macOS permission errors gracefully

**Done when:** two consecutive runs on this Mac produce a truthful diff; adding a 100MB file shows up as "changed".

## Phase 2 — Knowledge base + classifier (the "earning the right to delete" layer) (3–4 h)

- [x] `knowledge.py`: tiered entries for 50+ known paths:
  - **SAFE-REGENERABLE**: node_modules (regen: `npm install`), ~/.npm, pip cache, brew cache, DerivedData, .next/__pycache__, old .dmg installers in ~/Downloads
  - **CAUTION**: app caches that may hold state (Spotify offline music, WhatsApp media, JetBrains indexes), venvs (check requirements.txt exists), docker.raw (needs Docker flow)
  - **FORBIDDEN**: user data (Documents/Pictures/Desktop), credentials (~/.ssh, .env, keychains), git objects, active project source
- [x] `classify.py`: for each candidate attach evidence: known-rule (tier, regen command), git-activity (last commit age), process check (is owning app running?), last-access mtime, size
- [x] Unknown paths → LLM classification with the knowledge base in context; result gets logged back into memory (Phase 6)

**Done when:** every candidate carries a risk tier + evidence line + regeneration cost; the Spotify path classifies CAUTION *because* Spotify is running and cache holds offline data.

## Phase 3 — Planner + human gate (ground rule 04) (2 h)

- [x] `plan.py`: stable candidate IDs (`cand-001`…), grouped tiers, sorted by size×safety; proposal = exact path, GiB, tier, evidence, regen cost, proposed action
- [x] `gate.py`: low-risk → one batch approval; caution → per-ID approval; forbidden → refused outright, never proposed; irreversible simulator/system ops → typed confirmation phrase
- [x] Interactive CLI + `--yes-file` mode (scripted approval for evals and trajectories)

**Done when:** nothing executes without an explicit approved ID; forbidden paths never appear as actionable.

## Phase 4 — Executor (trash-first, never rm) (1–2 h)

- [x] `execute.py`: per approved ID: **revalidate exact path identity** (byte-for-byte path + fingerprint vs. plan snapshot), then move to `~/.spaceward/quarantine/` (own trash, restorable via `spaceward restore <id>`), log action to JSONL
- [x] Never `rm -rf`; never touch paths outside approved list; running-process check before each move

**Done when:** a scripted end-to-end run on fixture data moves only approved paths, quarantined files are restorable byte-identical.

## Phase 5 — Verifier + sign-off report (the quality bar) (2 h)

- [x] `verify.py`: df before/after (honest APFS delta — candidate sizes ≠ recovered space), app health checks (Spotify launches, `npm install --dry-run` passes on touched projects), cache-regen spot check
- [x] `report.py`: the artifact a person signs their name to — what changed, why safe, what was verified, GB actually recovered, restored-undo instructions

**Done when:** a full run on this Mac yields a report where every deleted path has evidence + verification result.

## Phase 6 — Memory (rubric: carries information forward) (1–2 h)

- [x] `memory.py`: persistent accept/reject ledger per path-pattern; auto-skip previously rejected paths in future plans ("you rejected ~/Music twice — not proposing again"); learned classifications from Phase 2 cache here
- [x] `spaceward memory show|forget` for transparency

**Done when:** a rejected candidate never re-proposes; verdict survives restarts.

## Phase 7 — Watch mode (the "preventive" in guardian) (1 h)

- [x] `spaceward watch`: poll df every N min; on free-space < threshold (default 10%) → trigger the loop
- [x] Demo path: manual `spaceward run --simulate-threshold` so judges reproduce the trigger deterministically

**Done when:** lowering the threshold triggers a full run end-to-end.

## Phase 8 — Baselines + eval harness (measured improvement, 15 pts) (3–4 h)

- [x] **B1 manual:** document this morning's real session (3.2→7.7GB, ~20 min) as the human baseline
- [x] **B2 naive script:** `clean.sh` — find top `du` offenders, `rm -rf` known dir names. Fast, blind
- [x] **B3 basic agent:** one general-purpose prompt + basic shell tools, no ledger/gates/verification
- [x] `eval/cases.py`: 10+ cases on identical fixture state, including traps:
  1. Spotify-style cache holding offline app data (the lived trap)
  2. node_modules in git-*active* project vs dormant one
  3. venv with requirements.txt present (recoverable) vs. orphaned
  4. Path that *suddenly grew* overnight (differential catches; size-ranking misses)
  5. Credentials-adjacent path that looks disposable
  6. macOS "System Data" gray zone
  7. App-support dir shared by two apps
  8–10+. benign standards: old installers, pip/npm caches, build artifacts
- [x] `eval/harness.py`: same cases through B1/B2/B3/Spaceward; score = **safe GB reclaimed with zero integrity failures**, human time per task, false-positive deletions, cost per task (brief's table format)

**Done when:** results/ holds one JSON + one comparison table per baseline, same cases, one trap case where B2/B3 demonstrably break something and Spaceward doesn't.

## Phase 9 — Changelog with real evidence (15 pts) (1 h, ongoing)

- [x] `CHANGELOG.md`: baseline → v0.1 naive script (fails traps: knowing paths ≠ knowing safety) → v0.2 knowledge base → v0.3 differential ledger → v0.4 approval gate → v0.5 memory+verification → final; each entry = tried/why, measured result (same harness), decision
- [x] Identify the single biggest contributor; document at least one removed experiment + what it taught

## Phase 10 — Reproducibility + video + trajectories (15 + 5 pts) (3 h)

- [x] `REPRODUCTION.md`: clean-env setup (uv, API key optional via heuristic mode), exact commands for B1/B2/B3/solution/eval, pinned versions, fixture seeding, expected outputs, runtime + cost
- [x] `trajectories/`: JSONL transcripts — scout phase, an unknown-path LLM classification, a human-gate interaction, one retry/verification event
- [x] `video/script.md`: 0:00 problem (99% full disk) → baseline walk → one live run start-to-finish → comparison table → changelog highlights → top contributor + removed experiment

## Phase 11 — Submission polish (1 h)

- [x] README final: user, bottleneck, value, four-questions framing
- [x] Ground-rules audit: sandboxed destructive ops (04), no secrets in repo (08), every claim → evidence file (09), judges can run everything (10)
- [x] Tag `v1.0`, package deliverables

---

## Working order & effort

| Order | Phase | Est. | Rubric served |
|---|---|---|---|
| 1 | P0 scaffold | 0.5h | — |
| 2 | P1 scout+ledger | 2.5h | Agent eng (30) |
| 3 | P2 knowledge+classify | 3.5h | Agent eng (30) |
| 4 | P3 gate + P4 execute | 3h | Ground rules, quality (20) |
| 5 | P5 verify+report | 2h | Quality (20) |
| 6 | P6 memory | 1.5h | Agent eng (30) |
| 7 | P7 watch | 1h | Differentiation |
| 8 | P8 baselines+eval | 3.5h | Measured improvement (15) |
| 9 | P9 changelog | 1h | Measured improvement (15) |
| 10 | P10 repro+video+traj | 3h | Reproducibility (15), video |
| 11 | P11 polish | 1h | End-to-end (20) |

**Total: ~22.5h build + eval.** Milestone checkpoints: after P4 (first safe end-to-end), after P8 (numbers exist), after P10 (submittable).

## Risks / pre-decided calls

- **Crowded space** → differentiation is structural (push vs pull, differential vs absolute, verify-after). We say this plainly in README instead of hiding it.
- **LLM nondeterminism in evals** → heuristic provider mode for judge runs; LLM mode shown in trajectories.
- **macOS permissions (Full Disk Access)** → scout degrades gracefully, reports "Blocked/Needs check" per path instead of partial silent success.
- **Scope creep** → server/CI story stays narrative-only; code ships laptop-first.
