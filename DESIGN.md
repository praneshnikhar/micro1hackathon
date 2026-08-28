# Spaceward — Design Doc
**The disk guardian: investigates before your disk fills, deletes nothing without your approval, verifies nothing broke after.**

micro1 Agentic Workflows Hackathon · Pranesh · Aug 2026

---

## 01 Who has this problem?

**Developers on storage-constrained machines** — anyone with a 256–512GB laptop running 8–12 dev tools. Each tool (npm, pip, Docker, Xcode, brew, venvs) downloads, caches, and *never deletes*. No tool coordinates with the others. The disk fills gradually, then all at once — usually via `ENOSPC: no space left on device` mid-build, a failed macOS update, or an IDE crash. This is a documented pattern ("catastrophic event" — reclaimr.dev, dev.to postmortems). Secondary: self-hosted CI runners and servers where a full disk breaks pipelines at 3AM.

The builder is the user: this session began with a 99%-full disk (3.2GB free on a 228GB Mac).

## 02 What bottleneck makes it worth solving?

The problem is **not** finding big files — DaisyDisk does that. It is two things:

1. **Opacity.** Existing cleaners show "what's big" but cannot say what is *safe* to delete. A "cache-looking" path may hold app state, offline media, licenses, or login data. One-click cleaners collapse scan/review/delete into one action (StorageRadar: "the problem is not cleanup itself; the problem is opaque cleanup").
2. **Reactivity.** Every scanner is pull-based — you run it when you remember, which is exactly after the ENOSPC. Nobody answers the question that matters at crisis time: **"what changed since things were fine?"**

Solving it converts a 20–60 minute manual, fear-laden investigation (this morning's real session: 20+ min of `du` spelunking, batch-by-batch approval, 4.5GB) into a minutes-long, evidence-backed, approval-gated loop.

## 03 Does the agent solve it well? — Architecture

One agent loop, six staged tool phases. No multi-agent theater — purposeful components only (brief: "purposeful choices matter more than the number of components").

```
trigger (free space < threshold, or manual run)
   │
   ▼
1. SCOUT      snapshot ledger + differential: "what changed since last scan?"
              tools: df, du-over-manifest, mtime/size manifest diff
   ▼
2. CLASSIFY   risk tiers per candidate path, with evidence
              skill: dev-cache knowledge base (regenerable / caution / forbidden)
              context: is repo git-active? is the app running? regeneration cost?
   ▼
3. PLAN       itemized proposal: candidate ID, exact path, GiB, risk,
              regeneration cost, evidence, proposed action (trash-first)
   ▼
4. HUMAN GATE explicit approval per candidate ID (batch for low-risk;
              individual + confirmation phrase for caution/irreversible)
              memory: past accept/reject decisions respected automatically
   ▼
5. EXECUTE    path-identity revalidation → move to Trash (undoable) → log
   ▼
6. VERIFY     df delta (honest APFS accounting), app/build health checks,
              cache regeneration spot-checks → sign-off report
```

**Capability → rubric mapping:**
| Agent capability | Where it lives | Rubric row |
|---|---|---|
| Better context | Differential ledger ("what changed"), git-activity, running-process checks | Agent Solution (30) |
| Tools | Manifest scanner, Trash-first mover, verifier runner, package-manager knowledge | Agent Solution (30) |
| Memory | Per-machine accept/reject ledger; learned safe/unsafe classifications persist | Agent Solution (30) |
| Verification | Post-cleanup health checks; pre-flight regeneration-cost proof | Agent Solution (30), End-to-End (20) |
| Skills | Encoded filesystem-risk knowledge base (50+ tool paths, tiered) | Agent Solution (30) |
| Orchestration | Staged single loop with hard gates between consequential phases | Agent Solution (30) |
| Human approval | Gate 4 — ground rule 04 satisfied by design | Ground rules |

**Stack:** Python 3.12 + `uv` (single-project, subprocess-friendly). LLM provider pluggable; trajectories logged as JSONL for the submission. Runs on macOS/Linux; laptop is the demo env, server/CI is the story.

## 04 Can another person reproduce it? — Evaluation design

**Baselines (same machine state, same eval cases, same rubric):**
- **B1 — Manual process:** the real thing, documented live this morning (20+ min, 4.5GB, human drives everything)
- **B2 — Naive script:** `find` + `du` top offenders, `rm -rf` known dir names. Fast, blind — fails trap cases
- **B3 — General agent, basic prompt:** "my disk is full, clean it" with generic tools. No ledger, no gates, no verification

**Primary metric:** safe bytes reclaimed with zero verification failures (GB × integrity).
**Secondary:** human time per task; false-positive deletions (must be 0 for Spaceward).
**Cases:** 10+, incl. challenging traps planted on real machine state:
1. **The Spotify trap** (lived this morning): `~/Library/Caches/com.spotify.client` looks like cache, holds offline music — B2 deletes it without knowing; Spaceward flags app-running + regeneration cost
2. node_modules in a **git-active** project vs. a dormant one
3. `venv` referenced by an active workflow vs. orphaned
4. A directory that *suddenly grew* 5GB overnight (differential catches it, scanners rank it by size only)
5. Credentials/config-adjacent path that looks disposable
6. macOS "System Data" gray zone
7. App-support dir shared by two apps
…plus benign standard cases (old installers, pip/npm caches, build artifacts) to fill 10+.

**Repro:** clean-env guide (uv, one command per baseline + solution), pinned versions, seeded fixture dir for judges without a full disk, expected outputs per case.

## Improvement Changelog (planned — to be filled with real evidence)

| Stage | What tried & why | Evidence | Decision |
|---|---|---|---|
| Baseline | Manual session (real, this morning) | 3.2→7.7GB, ~20 min, 4.5GB | Starting point |
| v0.1 | Naive script — is knowledge enough? | fails trap cases (Spotify, active project) | removed; learned "knowing paths ≠ knowing safety" |
| v0.2 | + risk skill (tiered dev-cache KB) | catches known paths, fails unknown | kept |
| v0.3 | + differential ledger (what changed) | catches overnight-growth case; faster scans | kept |
| v0.4 | + approval gate, candidate IDs, trash-first | 0 destructive errors | kept |
| v0.5 | + memory + verification loop | rejections respected; breakage caught pre-handoff | kept |
| Final | combined | TBD | main contributor identified |

*(entries replaced with measured results as built; removed experiments documented with what they taught)*

## Hot Take (draft)

Everyone builds scanners because scanning is measurable; nobody builds guardians because prevention is invisible. The hard problem was never finding space — it's **earning the right to delete**: evidence, regeneration cost, human trust, and proof afterward. Agents don't win here by being bigger calculators; they win by being auditable.

## Deliverables checklist (per brief)

- [ ] Solution code + README (user, bottleneck, value) + changelog with real evidence
- [ ] Reproduction guide: clean env, exact commands (B1/B2/B3/solution/eval), versions, runtime, cost
- [ ] 5-min video: problem → baseline → one live execution → comparison → changelog → top contributor + one removed experiment
- [ ] Agent trajectories: JSONL transcripts per agent phase, incl. one human-gate interaction and one retry/verification event

## Ground rules compliance

Consequential actions: trash-first + itemized approval + confirmation phrases (rule 04). No credentials or private data in submission (08). All claims tied to logged runs/df evidence (09). Judges run it on their own machine (10).
