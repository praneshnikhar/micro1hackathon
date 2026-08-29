# Spaceward

**The disk guardian: it investigates what changed before your disk fills, classifies deletion safety with evidence, deletes nothing without your explicit approval, and verifies nothing broke afterward.**

Built for the [micro1 Agentic Workflows Hackathon](https://github.com/praneshnikhar/micro1hackathon).

```
disk low: 3.3% free — investigating what changed

what changed since last scan:
  GROWN  +40.0 MB  builds/active-web/.next
  NEW    40.0 MB   builds/active-web/.next/cache-chunk.bin

refused (2): never proposed for deletion
  ref-001  60 MB  Docker.raw          — destroys all images; use docker system prune
  ref-002  40 MB  backup-server-key.pem — secret material

proposal (9 candidates):
  cand-001  [ SAFE  ]  50 MB  builds/active-web/.next
           regeneration=regenerated on next next build/dev
  cand-009  [CAUTION]  36 MB  projects/active-app/node_modules
           note=project_git_activity=0d ago; active project, downgrade for workflow safety

  cand-001: quarantined -> ~/.spaceward/quarantine/cand-001/.next
quarantined: 144.0 MB (planned)
verification: 4/4 passed
report: ~/.spaceward/reports/20260829-105859.md
```

## 01 Who has this problem?

Developers on storage-constrained machines. Every dev tool — npm, pip, Docker, Xcode, brew, Gradle, Rust — downloads, caches, and never deletes. None of them coordinate; nobody watches the total. The disk fills gradually, then all at once: `ENOSPC` mid-build, a failed macOS update, an IDE crash. The builder is the user: this project started the morning the disk hit 99%.

## 02 What bottleneck makes it worth solving?

The problem is not finding big files — DaisyDisk does that for $10. It is two things:

1. **Opacity.** Cleaners show "what's big" but cannot say what is *safe* to delete. A cache-looking path may hold offline music, app state, or licenses. The naive script in our eval matches Spaceward's recall exactly — and breaks 6 things doing it.
2. **Reactivity.** Every scanner is pull-based: you run it when you remember, which is after the crisis. Nobody answers the question that matters: **"what changed since things were fine?"**

## 03 Does the agent solve it well?

One agent loop, six staged phases — trigger → scout+diff → classify → itemized plan → **human gate** → quarantine → verify → sign-off report. Every agent capability does measurable work:

| Capability | Where it lives | What it earns |
|---|---|---|
| Better context | Differential ledger, git-activity, running-process checks | 100% recall at 0 breakage (git downgrade alone removes the worst false positive) |
| Tools | Manifest scanner, Trash-first mover with fingerprint revalidation, verifier probes | Honest APFS accounting; restorable deletions |
| Memory | Per-machine accept/reject ledger | Rejected paths never re-proposed |
| Verification | df delta, app/build health checks after every run | Breakage caught before handoff, never after |
| Skills | 50+ path knowledge base, tiered with regeneration costs | Refusals are evidence-backed, not vibes |
| Human gates | Candidate IDs, tiered approval, confirmation phrases | Ground rule 04 by design |

Full architecture: [DESIGN.md](DESIGN.md). Why each piece exists: [CHANGELOG.md](CHANGELOG.md).

## 04 Measured result (12-case fixture, identical state for all systems)

| Metric | B1 manual | B2 naive script | B3 basic agent | **Spaceward** |
|---|---|---|---|---|
| Safe bytes reclaimed | 108 MB | 194 MB | 144 MB | **194 MB** |
| Integrity failures | 0 | **6** | 1 | **0** |
| Recall | 56% | 100% | 74% | **100%** |
| Human time per task | 20 min (real session) | 2 min | 3 min | **2 min** |

The naive script matches our recall exactly and still breaks 6 things. That single number is the thesis: **recall is easy, earning the right to delete is the product.**

## Quickstart

```bash
uv sync
uv run python eval/run_eval.py        # reproduce the full comparison (~90 s, $0)
uv run spaceward run --dry-run        # plan-only on your machine
```

Full guide: [REPRODUCTION.md](REPRODUCTION.md).

## Deliverables map

| Brief item | Where |
|---|---|
| 01 Code + changelog | this repo, [CHANGELOG.md](CHANGELOG.md), [plan.md](plan.md) |
| 02 Reproduction guide | [REPRODUCTION.md](REPRODUCTION.md) |
| 03 Solution video | [video/script.md](video/script.md) (5-min script) |
| 04 Agent trajectories | [trajectories/](trajectories/) |

## Ground-rules audit

- **04 Sandbox/human approval**: all deletions are quarantine moves gated on itemized approval; irreversible ops require typed confirmation; no-TTY runs refuse to execute
- **08 No credentials/private data**: state lives in `~/.spaceward/` (gitignored by location, never in-repo); fixture data is synthetic
- **09 Claims → evidence**: every number above regenerates from `eval/run_eval.py`; trajectories are logged JSONL
- **10 Judges can run it**: clean-env guide with expected outputs, pinned versions, $0 cost
