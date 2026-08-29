# Improvement Changelog

The story of Spaceward, from a manual cleanup session to a preventive guardian agent.
Every entry is measured with the same 12-case fixture harness (`eval/`) unless marked as a real-machine observation.

**Baseline established 2026-08-29, this machine, real session** (documented in `baselines/b1_manual/README.md`).

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| **Baseline** | Manual disk-cleanup process: human runs `du`/`df`, inspects top dirs, deletes batch-by-batch with per-item judgment | 3.2 → 7.7 GB free, ~20 min wall time, 4.5 GB reclaimed, zero breakage | Starting point. Safe but slow, fear-laden, and entirely dependent on human attention. Repeats every few months |
| **v0.1 Naive script** (kept as baseline B2) | Size-greedy shell rules: delete every `node_modules`/`.next`, every file >30MB | Eval: 194 MB reclaimed (100% recall) but **6 integrity failures** — deleted offline music cache, active project deps, a credentials file, two app databases, Docker's VM disk | Removed as product, kept as baseline. Learning: **knowing paths ≠ knowing safety**. Recall is easy; precision is the product |
| **v0.2 Knowledge base + risk tiers** | Encoded 50+ tool paths as SAFE (regenerable, with regen command) / CAUTION (may hold state) / FORBIDDEN (never proposed) | Eval: standard safe paths tiered correctly; credentials and Docker.raw refused outright. But active project's `node_modules` still proposed SAFE — no context | Kept. Tiers + evidence lines became the core review artifact. Learning: a refusal list is as valuable as a deletion list |
| **v0.3 Differential ledger** | Store scan manifests; diff consecutive scans to answer "what changed since things were fine?" instead of "what's biggest?" | Eval sudden-growth case: plan context shows `GROWN +40MB builds/active-web/.next` even though it ranks mid-size. Real machine: surfaced phantom `GROWN +18GB` → traced to incomplete-subtree propagation bug; fixed so partial scans can never produce false alarms. Also caught same-second manifest overwrite that silently disabled all diffs | Kept. This is the structural differentiator vs every scanner in the space. Learning: differential data is only trustworthy if *completeness propagates* — partial data must be marked, never averaged |
| **v0.4 Approval gate + quarantine** | Itemized candidate IDs; batch approve for SAFE, per-item for CAUTION; all deletions move to restorable quarantine; fingerprint revalidation before every move; refuse-to-execute without TTY or yes-file | Interactive session (`trajectories/`): 4 SAFE approved, 4 CAUTION rejected, execution 4/4 verification passed, quarantine restores byte-identical. Non-interactive run without yes-file refused: `refusing to execute` | Kept. Ground rule 04 satisfied by design. Learning: the gate is the product — agents propose, humans dispose |
| **v0.5 Git-aware tier downgrade** | If a project-scoped artifact (`node_modules`, `target`, …) sits in a repo with a commit ≤7 days old, downgrade SAFE→CAUTION with the commit age as evidence | Eval trap `node_modules-active`: B3 (no context) deletes it — integrity failure; Spaceward downgrades and keeps it. **This change took Spaceward from 1 false positive to 0** | Kept. Learning: the cheapest context (one `git log` call) eliminates the most embarrassing failure mode |
| **v0.6 Eval-driven hardening** | Built the 4-system harness; fixed what it caught: landmark flags erased by growth-union (differential proposed a file instead of its regenerable parent), candidate floor vs fixture sizes, template hygiene in the harness itself | Spaceward: 194 MB reclaimed, **0 integrity failures, 100% recall**, 2 min human time | Kept. Learning: the harness paid for itself immediately — three real bugs surfaced on the first two runs |
| **Final** | Combined loop: trigger → scout+diff → classify (knowledge + context evidence) → itemized plan → human gate → quarantine → verify → sign-off report | Comparison table (below) | Main contributor: **context evidence (git activity + process checks)** — it is the single change that separates 0 breakage from 6 |

## Final comparison (same fixture, same 12 cases)

| Metric | B1 manual | B2 naive script | B3 basic agent | Spaceward |
|---|---|---|---|---|
| Safe bytes reclaimed (of 194 MB safe) | 108 MB | 194 MB | 144 MB | **194 MB** |
| Integrity failures (must be 0) | 0 | **6** | 1 | **0** |
| Recall of safe bytes | 56% | 100% | 74% | **100%** |
| Human time per task | 20 min (real) | 2 min | 3 min | **2 min** |
| Cost per task | $0 | $0 | $0 (proxy) | **$0** |

## Removed experiments

- **LLM-first classification.** The first design called the LLM for every candidate. Real run: HTTP 401 mid-eval and silent nondeterminism risk. Removed; classification is now deterministic (knowledge base + context evidence), with the LLM strictly optional for unknown paths (`--provider anthropic`). Baseline B3 retains an LLM mode for fair comparison.
- **Multi-agent orchestration.** A scout agent + classifier agent + planner agent was prototyped on paper. Rejected: same quality from one loop with staged phases, less overhead, easier trajectories. The brief's own rule — purposeful choices over component count — settled it.

## Hot take

Everyone builds scanners because scanning is measurable; nobody builds guardians because prevention is invisible. The hard problem was never finding space — it is **earning the right to delete**: evidence, regeneration cost, human trust, and proof afterward. The eval proved it in one number: the naive script matched Spaceward's recall exactly and still broke 6 things. Agents don't win here by being bigger calculators; they win by being auditable.
