---
name: delegation-parallelism
description: Invoke when deciding whether to split work across parallel agents/sessions or do it inline — tests scope independence, weighs coordination cost against the parallelism win, and sets an observation cadence for delegated work.
---
# Delegation & Parallelism

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- A task could be split into pieces that different agents or sessions might run at the same time.
- You are about to fan out N workers and are unsure whether the pieces are actually independent.
- You are doing serially something that has no ordering dependency and could overlap.
- Two candidate subtasks touch the same files, the same branch, or the same shared resource.
- You have delegated work and need to decide how often to check on it without babysitting.
- The coordination overhead of splitting might exceed the time the split would save.

## Core loop

1. **Decompose the task into candidate units and their outputs.**
   List the pieces and, for each, the files/resources it writes and the artifact it produces. You cannot
   reason about independence until you can see each unit's write-set.

2. **Apply the independence test to each pair.**
   Two units are parallel-safe only if their write-sets are disjoint AND neither consumes the other's
   output AND they share no serial resource (same branch, same DB row, same file, same port). If any of
   those holds, they are ordered or must be merged — not parallel.

3. **Enforce disjoint scope before splitting.**
   For units you will parallelize, make the scope boundaries explicit: which files each owns, which it must
   not touch. Overlapping write-sets across parallel workers produce merge conflicts that cost more than the
   parallelism saved. If you cannot carve disjoint scopes, do it inline.

4. **Weigh coordination cost against the parallelism win.**
   Estimate the split's overhead — briefing each worker, defining interfaces, merging results, resolving
   conflicts — against the wall-clock saved. Small or tightly-coupled tasks lose this trade; large,
   genuinely independent tasks win it. When the margin is unclear, keep it inline.

5. **Choose the delegation shape.**
   - Independent, disjoint, large → parallel workers, one scope each.
   - Sequential dependency → a pipeline; each stage starts when the prior's output exists.
   - Same scope / small / exploratory → inline, no delegation.
   - Needs a fresh, isolated context but not concurrency → one delegated session, awaited.

6. **Brief each delegate with a self-contained scope.**
   Give each worker exactly what it needs and no more: its goal, its owned files, its interface with others,
   its done-signal. A delegate that has to ask back mid-run erodes the parallelism you paid for.

7. **Set an observation cadence, not a stare.**
   Decide up front when you will check delegated work — at each unit boundary, on a fixed interval, or on a
   done-signal — and let it run between checks. Poll on meaningful transitions, not every tick.

8. **Merge and reconcile at boundaries.**
   Integrate results only at unit boundaries, verify the combined result, and resolve any conflict as a
   scoping lesson for next time. If two delegates collided, the split was wrong, not the workers.

## Heuristics

- Split only when write-sets are provably disjoint; overlapping writes make parallelism a conflict generator.
- If unit B consumes unit A's output, they are a pipeline, not a parallel pair — sequence them.
- 2+ genuinely independent large tasks → parallelize; anything small or coupled → inline and skip the overhead.
- Coordination cost scales with the number of shared interfaces; minimize interfaces before adding workers.
- One writer per file/branch/resource at a time; concurrent writers to one target is a merge tax, not speed.
- Observe delegated work at boundaries and done-signals, not continuously; a stare wastes the concurrency.
- If briefing a delegate takes longer than doing the unit, do the unit inline.
- Cap fan-out to what you can actually reconcile; 3 well-scoped workers beat 8 that collide on merge.
- When independence is uncertain, assume coupled and serialize — a false split is costlier than a missed one.
- A delegate that keeps asking clarifying questions signals an under-specified scope; re-brief, don't micromanage.

## Anti-patterns

- **False parallelism.** Fanning out workers onto pieces that share files or a branch, then paying it back
  in merge conflicts. → Corrective: run the independence test on write-sets first; only disjoint scopes split.
- **Coordination-dominated split.** Parallelizing a task so small that briefing and merging cost more than
  doing it. → Corrective: compare overhead to wall-clock saved; keep small/coupled work inline.
- **Pipeline run as parallel.** Launching a consumer before its producer's output exists, so it works from
  stale or empty input. → Corrective: sequence dependent units; start each when the prior's artifact is real.
- **Babysitting the delegate.** Polling a delegated session every few seconds, blocking on it as if inline.
  → Corrective: set a boundary/interval cadence and let it run; check on transitions, not ticks.
- **Fire-and-forget.** Delegating and never observing, then discovering at the end the worker went off-scope.
  → Corrective: define a done-signal and at least one mid-point boundary check.
- **Unbounded fan-out.** Spawning more workers than you can brief distinctly or merge cleanly.
  → Corrective: cap at the number of disjoint scopes you can actually reconcile.

## Relation to existing axes

- **vs incremental-safety:** incremental-safety sequences one change into safe intermediate states so the
  system stays green at every step — it is about *ordering edits over time*. Delegation-parallelism is about
  *distributing units across agents* — who does what, concurrently or not. One decomposes a change for
  safety; the other decomposes work for throughput and decides whether concurrency is even sound.
- **vs tradeoff-articulation:** tradeoff-articulation weighs alternative *designs* for one decision.
  Delegation-parallelism weighs one specific execution decision — split vs inline — with its own tests
  (write-set disjointness, coordination cost). It is the applied case, not the general design-choice method.

## Worked example

*Illustrative construction, not a recorded run.*

Task: "Add a new report type: backend query, API endpoint, frontend chart, and docs." One agent, could delegate.

```
Agent decomposes into 4 units with write-sets: query (db/reports.sql), endpoint (api/reports.ts),
    chart (web/ReportChart.tsx), docs (README).
Independence test pairwise: endpoint CONSUMES query's result shape → pipeline edge. chart CONSUMES
    endpoint's response schema → pipeline edge. docs depends on the final shape → last.
Conclusion: this is mostly a pipeline, not a parallel fan-out. Only query and a docs stub have disjoint
    write-sets early on.
Agent sequences: build query first (defines the schema), then endpoint and chart can proceed — and once the
    response schema is frozen, endpoint and chart ARE disjoint (api/ vs web/) → parallelize those two.
Agent scopes the two parallel workers: worker-api owns api/*, worker-web owns web/*, interface = the frozen
    schema; neither touches the other's dir.
Observation cadence: check at the schema-freeze boundary and at each worker's done-signal, not continuously.
Merge at boundary: both land, agent verifies the combined flow end-to-end, writes docs last.
Exit: coordination paid off only for the two truly-disjoint units; the rest stayed a serial pipeline
    because their write-sets were coupled.
```

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
