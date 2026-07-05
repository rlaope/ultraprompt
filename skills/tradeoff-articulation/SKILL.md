---
name: tradeoff-articulation
description: Invoke when a design decision has multiple viable implementations and the choice affects performance, memory, complexity, or blast radius — forces enumerating real alternatives, quantifying the axes that matter, and recording what would reverse the decision.
---
# Trade-off Articulation

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- Two or more implementations would each pass the tests, but they differ on latency, memory, throughput, operational complexity, or blast radius.
- You are about to pick a data structure, storage layout, locking strategy, caching policy, consistency model, or protocol — categories where the "obvious" choice is often only obvious because alternatives were never named.
- A reviewer, teammate, or future session will need to understand *why* this shape was chosen, not just *what* was chosen.
- The decision is expensive to reverse (schema, wire format, public API, on-disk layout) or its cost scales with data/traffic growth.
- You notice yourself justifying a design after writing it instead of before — that is the signal to stop and run this loop retroactively.
- Do NOT apply when one option strictly dominates (better or equal on every axis you care about) or the decision is trivially reversible in one commit — name the dominant option in one sentence and move on.

## Core loop

1. **State the decision as a question with a scope.**
   - One sentence: "How should X handle Y, given constraint Z?"
   - If you cannot phrase the constraint, you do not yet know enough to decide — go measure or read first.
2. **Timebox the analysis before starting it.**
   - Budget proportional to reversal cost: minutes for a reversible internal choice, 10x longer for a persisted format or public contract.
   - Write the budget down. When it expires, decide with what you have.
3. **Enumerate 2-4 real alternatives.**
   - Each must be something you would actually ship — no strawmen inserted to make the favorite look good.
   - If you can only produce one candidate, either the decision is dominated (skip deliberation, say so) or you have not explored enough (spend part of the timebox searching for a second).
4. **Name the axes that matter for THIS decision, then drop the rest.**
   - Typical axes: latency (p50/p99), memory footprint, write/read amplification, implementation complexity (LOC, new dependencies, new failure modes), blast radius (what breaks if this is wrong), migration/reversal cost.
   - Three axes is usually right; more than five means you haven't decided what matters.
5. **Quantify each cell, even roughly.**
   - Prefer measured numbers; accept back-of-envelope estimates with stated assumptions ("~10^5 entries × 64B ≈ 6.4MB — fits in RAM easily, not in L2").
   - Order-of-magnitude precision is enough to eliminate most options.
   - Mark unmeasured cells explicitly as estimates — never silently mix measured and guessed numbers.
6. **Kill dominated options first.**
   - Any alternative that is worse-or-equal on every relevant axis dies immediately.
   - What remains is a genuine trade-off frontier — usually 2 options.
7. **Choose, and state the reason as a priority ordering.**
   - "We pick A because p99 latency matters more than memory here, because <requirement/SLO/constraint>."
   - The reason must reference the axes from step 4, not vibes ("cleaner", "more elegant") — if an aesthetic property matters, translate it into an axis (maintenance cost, review time, bug surface).
8. **Record the reversal condition.**
   - One or two lines: "Revisit if entry count exceeds ~10^7, if the dependency is deprecated, or if profiling shows this path above 5% of CPU."
   - This is the highest-value artifact — it converts a frozen decision into a monitored one.
9. **Write the record where the code lives, then implement only the winner.**
   - A 5-10 line comment block, ADR stub, or commit-message section. Minimal template:

     ```text
     DECISION: <the question from step 1>
     CONSIDERED:
       A: <one line>  — rejected: <losing axis + magnitude>
       B: <one line>  — chosen
     WHY: <priority ordering over the axes, tied to a requirement>
     REVISIT IF: <numeric trigger(s) someone can observe or alert on>
     ```

   - Do not hedge by half-implementing two options.

## Heuristics

- If reversal cost is one commit, the analysis budget is ~2 minutes; if it's a data migration or API break, budget 10x more.
- 2 alternatives is the minimum for a real decision; 4 is the maximum worth tabulating — beyond that, cluster options into families first and decide between families.
- An estimate within 10x is enough to kill an option; only measure precisely when the frontier options are within 10x of each other on the deciding axis.
- If every axis favors the same option, stop building the table — declare dominance in one sentence and implement.
- Complexity is quantifiable: count new dependencies, new concurrent interactions, and new failure modes an on-call engineer must understand. Each is a number, not a feeling.
- Blast radius question to always ask: "if this choice is wrong, what is the worst artifact — a slow endpoint, corrupted data, or a wire format we support forever?" Corruption and forever-formats justify blowing the timebox.
- When two frontier options tie after quantification, pick the one cheaper to reverse and tighten the reversal condition's trigger.
- If you are researching a fifth axis or a fifth alternative, the timebox has failed — decide now with the table you have.
- A hard constraint (SLO, memory ceiling, compliance rule) is not an axis to weigh — it is a filter applied before the table. Filter first, weigh what survives.
- If a decision keeps resurfacing across sessions, the recorded reversal condition was too vague — rewrite it with a numeric trigger someone can alert on.
- Never let the deciding axis be the one you cannot estimate: either spend part of the timebox getting a rough number for it, or demote it and decide on the axes you can score.
- The comparison table belongs in the repo only when reversal cost is high (ADR-worthy); for cheap decisions the table lives in your reasoning and only the WHY + REVISIT IF lines get written down.
- Estimates that decided the outcome deserve a follow-up measurement hook (metric, benchmark, assertion) — an estimate that stays unvalidated is a latent wrong decision.

## Anti-patterns

- **Post-hoc rationalization** — writing the justification after the code, fitting reasons to the choice already made.
  → Corrective: run steps 3-6 before writing the implementation; if code already exists, honestly ask whether option B would survive the same table.
- **Strawman alternatives** — listing "do nothing" and one absurd option next to the favorite so the comparison is theater.
  → Corrective: every listed alternative must be one you would defend shipping; delete any you wouldn't.
- **Unbounded deliberation** — endlessly refining estimates on a decision that costs one commit to reverse.
  → Corrective: set the timebox in step 2 and treat expiry as a hard decision trigger; cheap-to-reverse means decide fast and instrument.
- **Qualitative mush** — a table full of "fast / faster / simpler / cleaner" with no numbers.
  → Corrective: replace every comparative adjective with a magnitude and a unit, even if estimated ("~2x allocations per request", "+1 dependency, +300 LOC").
- **Decision without a reversal condition** — choosing correctly for today's load and never noticing when the assumption breaks.
  → Corrective: always write step 8's trigger; if you can't name what would change your mind, you haven't understood why you chose.
- **Hedged implementation** — keeping both options half-alive behind a flag "just in case," doubling the maintenance surface.
  → Corrective: implement the winner fully; the reversal condition, not dead code, is your insurance.

## Worked example

*Illustrative construction, not a recorded run.*

Task: rate limiter for ~100k req/s across 4 API nodes.

- Agent states the question → "How to enforce a per-key sliding-window limit across nodes, given p99 budget 2ms and tolerable over-admission ≤5%?" — because without the 5% tolerance the exactness axis cannot be scored.
- Agent sets the timebox → 15 minutes of analysis, no prototype — because the choice is wire-adjacent in behavior but internally reversible (no persisted format, no public API).
- Agent enumerates 3 real alternatives:
  - (A) Redis sorted-set exact sliding window.
  - (B) Redis fixed-window counters with two-bucket interpolation.
  - (C) Local in-process token buckets with async counter sync.
- Agent names 4 axes → added p99 latency, Redis load, over-admission %, failure blast radius — and drops "code elegance" because it doesn't survive translation into a measurable axis at this size.
- Agent quantifies (est = back-of-envelope, marked):

  | Axis | A: ZSET exact | B: two-bucket | C: local buckets |
  |------|---------------|---------------|------------------|
  | Added p99 latency | 1 RTT + O(log n) ZSET ops | 1 RTT, 2 INCR | ~0 hot path (est) |
  | Redis load | high: ZADD+ZREMRANGE+ZCARD per req | 2 ops per req | ~0.1 op per req (est) |
  | Over-admission | 0% (exact) | ~3-5% at window boundary (est) | ~10-20% worst case, N nodes × sync interval (est) |
  | Redis-outage behavior | limiter down | limiter down | degrades gracefully |

- Agent kills the dominated option → A dies: B is cheaper on every axis except exactness, and 3-5% error sits inside the stated 5% tolerance, so exactness buys nothing here.
- Agent resolves the frontier (B vs C) → B wins accuracy; C wins latency and outage behavior. Priority ordering from constraints: the 5% over-admission tolerance is a hard product requirement (C's 10-20% estimate fails the filter under worst-case sync lag), and the 2ms p99 budget comfortably fits one Redis RTT. Picks B.
- Agent records the reversal condition in the module docstring → "Revisit toward local buckets (option C) if Redis p99 RTT exceeds 1ms under load, node count exceeds ~20, or a Redis outage postmortem shows limiter unavailability caused a cascading failure."
- Agent implements B only, and adds a metric on window-boundary over-admission — so the 3-5% estimate becomes a measured number and the table's weakest cell gets validated in production.
- Total deliberation cost: under the 15-minute timebox, one table, zero prototypes — and the record means the next engineer who proposes "just use local buckets" gets an answer with numbers instead of an argument.

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
