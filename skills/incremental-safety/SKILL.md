---
name: incremental-safety
description: Decompose a large or risky change into a sequence of independently safe intermediate states, so the system stays green at every step and any step can be reverted alone.
---
# Incremental Safety

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- The change touches 3+ files, crosses a module boundary, or alters a public interface, schema, or wire format.
- You are migrating between technologies (framework swap, storage engine, protocol version) while the system must keep running.
- The change cannot be verified in one shot — the test suite, a benchmark, or production traffic is the only real oracle.
- Rollback matters: the target runs in production, other agents or humans work on the same tree, or the deploy is not atomic.
- A refactor started as "small" but the diff keeps growing and you have not committed anything runnable yet.
- You are about to do a big-bang rewrite and cannot state what proves the rewrite behaves identically to the original.

## Core loop

1. **Name the end state and the invariant.** Write one sentence for the target and one for what must stay true throughout,
   e.g. "all existing tests pass", "API responses byte-identical", "p99 within 5% of baseline".
   The invariant is the operational definition of "safe" for every intermediate state; if you cannot state it, you cannot know a step succeeded.
2. **Find the seam.** Identify the narrowest interface where old and new can coexist:
   a function boundary, an adapter or facade, a routing layer, a config flag, a duplicated column.
   If no seam exists, your first change is to *create* one — extract an interface, funnel scattered call sites through a single wrapper — with zero behavior change.
   Seam-creation commits are mechanical and easy to verify; they buy safety for everything after.
3. **Plan backward from the end state as a step ladder.** List steps such that:
   - each step leaves the system fully working (the invariant holds),
   - each step is independently revertable without conflicting with later steps,
   - each step is verifiable by an existing check or by a check the step itself adds.
   If a candidate step fails the first condition, split it. Order steps so the riskiest one lands when the blast radius is smallest — after reversible steps have proven the design, before irreversible cleanup.
4. **Add the new alongside the old — never replace in the same step.** Strangler-fig: introduce the new path dark
   (unreferenced, or behind a flag defaulting to the old path). Commit it.
   The old path is your rollback mechanism; deleting it now would destroy the very thing that makes the migration safe.
5. **Parallel-run before cutover whenever outputs are comparable.** Route real inputs through both paths and compare:
   shadow traffic, dual-write with reconciliation, golden-file diffing, or characterization tests executed against both implementations.
   Cut over only when the diff count over a meaningful sample is zero, or every remaining diff is individually explained and explicitly accepted.
6. **Cut over reversibly.** Flip the flag, switch the route, or swap the import as its own minimal commit.
   The cutover commit contains *only* the switch — no cleanup, no drive-by fixes — so reverting it restores the old path instantly without touching the new code.
7. **Verify at the invariant after every step, not just at the end.** Run the invariant's check (tests, diff harness, benchmark) after each commit.
   A red intermediate state means the step was too big — revert or split it.
   Do not "push through and fix at the end"; that converts a step ladder back into a big bang.
8. **Delete the old path as a separate final step.** Only after the new path has survived verification — and, in production settings, a soak period.
   Removal is its own commit: pure deletion, trivially reviewable, and it marks the migration's true completion. Until it lands, the migration is open.
9. **Watch for scope creep and re-plan when detected.** If mid-step you discover the change fans out —
   new callers, hidden coupling, schema implications, an undocumented feature the new path can't express — stop.
   Commit or stash the green portion, restate the end state, and re-run steps 2–3 with the new information instead of absorbing the growth silently.

## Choosing seam points

The seam determines the size of the risk window; choose it deliberately, not by convenience.

- **Prefer data boundaries over call boundaries** when the two sides deploy independently — serialized formats, DB rows, and message payloads outlive processes, so a seam there survives partial deploys.
- **Prefer one choke point over many.** A seam through which all traffic already flows (single entry function, one router, one loader) needs one cutover commit; a seam scattered across N call sites needs N flips and gives you N chances to miss one. Funnel first.
- **Prefer seams with an existing oracle.** If the boundary already has tests, logs, or metrics on it, you get parallel-run comparison nearly for free.
- **Minimize the interface you freeze.** Everything crossing the seam is frozen until cutover completes; a fat seam blocks unrelated work for the whole migration. Narrow it before starting.
- **Check both directions.** A good seam lets the old call the new (strangler) *and*, if needed, the new fall back to the old (safety net). If only one direction works, know which one you have.

## Heuristics

- If you cannot describe an intermediate state in which both old and new code exist and everything works, you have not found the seam yet — keep looking before writing any new-path code.
- A step is right-sized when its diff is reviewable in one sitting and its revert is a single `git revert` with no conflicts against later steps.
- Expand-migrate-contract for any schema or interface change: add the new field/method (expand), move all readers then all writers (migrate), remove the old one (contract). Never combine expand and contract in one commit.
- Flags are for cutover, not for living architecture: every flag you add gets a removal step written into the plan at creation time. A flag that outlives its migration is debt that doubles a test matrix.
- Parallel-run cost check: if comparing old vs new outputs costs less than one production incident, run both. It almost always does.
- Diff-size tripwire: if the working diff exceeds roughly 2x your estimate, or you touch a file you did not plan to touch, treat it as a hard signal to stop and re-plan — the "small change" has silently become a big one.
- Riskiest-step placement: do irreversible or hard-to-verify steps (data backfills, destructive renames, dropped columns) as late as possible, after everything reversible has already proven the design.
- When the test suite is weak, write characterization tests against the *old* behavior first; they double as the parallel-run harness and the invariant check.
- Commit cadence is a safety mechanism: commit every time you return to green, even if the message is boring. Uncommitted green states cannot be reverted to.
- Refactoring commits and behavior-changing commits never mix: a pure-move commit is provably behavior-preserving and lets `git bisect` do its job; a mixed commit blinds both reviewers and bisect.
- During parallel-run, treat every old-vs-new mismatch as "old is the spec" by default. Improving semantics is a separate change after cutover; conflating fidelity with cleanup is how migrations grow unbounded.
- Count the states you must keep working, not the lines you change: a 10-line edit that leaves the system broken for an hour is bigger than a 500-line mechanical rename that is green throughout.

## Cutover readiness checklist

Answer all five before flipping the switch; a "no" on any of them means the cutover step is premature.

1. Has the new path processed representative real inputs (not just unit-test fixtures), and were its outputs compared against the old path's?
2. Is the rollback a single revert or flag flip that one person can execute in under a minute, and has it actually been exercised once?
3. Is the cutover commit free of any other change — no cleanup, no renames, no opportunistic fixes riding along?
4. Is there a signal that would tell you within one verification cycle that the cutover regressed the invariant (failing test, diverging metric, error-rate alert)?
5. Does the plan already contain the follow-up steps — soak, old-path deletion, flag removal — with the migration held open until they land?

## Anti-patterns

- **Big-bang replacement** — deleting the old implementation in the same change that introduces the new one.
  → Corrective: re-introduce the old path from history, put both behind a seam, and cut over as a separate flagged step.
- **Long-lived red branch** — a feature branch that stays broken for days and merges as one giant diff nobody can review or bisect.
  → Corrective: slice it into green steps landed sequentially into the mainline; if a slice cannot be green on its own, hide it behind a flag or land it as a dark, unreferenced module.
- **Refactor + behavior change in one commit** — reviewers and `git bisect` cannot separate the mechanical move from the semantic change, so a regression hides inside noise.
  → Corrective: pure-refactor commit first, then the behavior change as a small readable diff on top.
- **Cutover commit that also cleans up** — flipping the switch and deleting the old path together, so rollback requires resurrecting code instead of reverting one commit.
  → Corrective: split into a flip commit and a delete commit; delete only after the flip has soaked.
- **Silent scope absorption** — noticing mid-task that the change is bigger than planned and quietly continuing because "I'm already halfway".
  → Corrective: the moment an unplanned file or subsystem enters the diff, stop, commit the green portion, and re-plan explicitly with the new scope stated out loud.
- **Flag graveyard** — cutover flags left in the code after migration, so every future test run pays for both branches forever.
  → Corrective: schedule flag removal as the migration's final step and treat the migration as open until that deletion commit lands.

## Worked example

*Illustrative construction, not a recorded run.*

Task: replace a hand-rolled JSON config parser with a schema-validated loader across a service with 14 call sites.

- Agent estimates "small change, just swap the parser" — then applies the tripwire check: 14 call sites is a fan-out risk, so it plans incrementally anyway.
- Agent names the invariant first: *every call site receives an identical config object for all existing config files in the repo.*
- Agent looks for a seam → finds call sites import `parse_config()` directly from 6 different modules. No choke point exists, so step 0 is to create one.
- Step 0: add `config/loader.py` exposing `load()` that wraps the old parser; repoint all 14 imports. Purely mechanical, zero behavior change. Tests green → commit ("route all config loading through loader facade").
- Step 1: write the new schema-validated loader as `load_v2()` in the same module — dark, nothing calls it — plus unit tests for it. Commit. Old path untouched; this commit is trivially revertable and blocks nobody.
- Step 2: build the parallel-run harness — iterate every `*.json` config in the repo, run both `load()` and `load_v2()`, deep-diff the results.
- First harness run → 3 mismatches. Agent observes the old parser silently coerced `"8080"` to int while v2 rejects it → classifies this as a real behavioral difference, not a v2 bug.
- Agent adds explicit string-to-int coercion to the schema *because the invariant is "identical output", not "cleaner semantics"* — tightening semantics is queued as a follow-up change after cutover, not folded in.
- Second harness run → diff count 0 across all configs. Commit harness + coercion fix.
- Mid-task the scope tripwire fires: while fixing coercion, agent notices two config files use an undocumented `include` directive the schema cannot express. The diff is about to grow into "redesign config includes."
- Agent stops, keeps `include` handling in an unchanged pre-validation pass, and files the redesign as a follow-up instead of absorbing it — the migration ships on schedule with scope intact.
- Step 3 (cutover): `load()` body becomes `return load_v2(...)`. One-line commit, nothing else in it. Tests green. Rollback path: revert this single commit.
- Step 4 (contract): after one green CI cycle, delete the old parser and the harness's old-path arm. Pure deletion commit; migration closed.

Six commits, every one green, every one revertable alone. The riskiest discovery — the coercion mismatch — was caught by the parallel-run harness in seconds, not by production.

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
