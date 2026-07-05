---
name: hypothesis-management
description: Debug by maintaining 2-4 competing hypotheses with explicit evidence and kill criteria, choosing each probe to maximally discriminate between them instead of confirming a favorite.
---
# Hypothesis Management

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- A bug's cause is not obvious after the first read of the failing code path.
- The symptom admits more than one plausible mechanism (timing, data, config, environment, logic).
- The bug is intermittent, load-dependent, or only reproduces in one environment.
- A previous "fix" appeared to work, then the symptom returned or mutated.
- You notice yourself repeatedly probing the same suspect without decisive results.
- The failure is silent or indirect: wrong output, slow convergence, resource leak — anything where the crash site is far from the cause.

## Core loop

1. **State the symptom precisely.** One sentence, observable facts only: what happens, under what input/load/environment, how often. No causal language yet ("connection pool exhausted" is a hypothesis, "requests time out after ~30s under >50 concurrent users" is a symptom).
2. **Generate 2-4 competing hypotheses and write them down.** Each must name a concrete mechanism that would fully produce the symptom. Force them to be mutually distinguishable — if two hypotheses predict identical observations everywhere, merge them. If you can only think of one, deliberately generate its rivals: wrong layer (caller vs callee), wrong category (code vs data vs config vs environment), and "the symptom report itself is wrong."
3. **Attach a kill criterion to each hypothesis before probing.** Write: "H2 is dead if the log shows X" / "H3 is dead if the bug reproduces with feature Y disabled." A hypothesis without a stated kill criterion is a belief, not a hypothesis — sharpen it or drop it.
4. **Record current evidence for AND against each hypothesis.** Two columns per hypothesis. If the "against" column is empty for your favorite, you have not looked for counter-evidence yet — that is anchoring, not confidence.
5. **Choose the next probe by maximum discrimination.** For each candidate probe (log line, breakpoint, bisect, minimized repro, config flip), ask: how many hypotheses give different predictions for its outcome? Run the probe that splits the live set most evenly, not the one that would confirm the leader. A probe whose every outcome you'd explain the same way is worthless — skip it.
6. **Before running the probe, write down each hypothesis's predicted outcome.** This is the anchoring guard: predictions committed in advance cannot be retrofitted. After the probe, compare actual vs predicted per hypothesis.
7. **Execute kills mechanically.** If a probe outcome meets a kill criterion, mark the hypothesis DEAD with the evidence line — do not soften to "unlikely" and keep half-probing it. If evidence contradicts a prediction but misses the kill criterion, record it in the against column and consider tightening the criterion.
8. **When one hypothesis survives, attack it once more before declaring victory.** Design a probe specifically aimed at falsifying the survivor (step 5 in reverse). Only after it survives its own falsification attempt do you fix.
9. **Verify the fix explains ALL recorded evidence.** Walk the evidence table: every observation, including early "weird but ignored" ones, must be consistent with the confirmed mechanism. Unexplained residue means a second bug or the wrong diagnosis.
10. **Resurrect on contradiction.** If post-fix the symptom persists or new evidence conflicts with the survivor, do not patch the survivor's story ad hoc. Re-open the dead hypotheses, re-read their kill evidence in light of the new data (kill criteria are sometimes wrong), and re-enter the loop at step 4 with the updated table.

Maintain the table as a literal artifact — a scratch file or a comment block in the debugging session, not working memory:

```
SYMPTOM: <one observable sentence>

H1 <mechanism>            [LIVE|DEAD|RESURRECTED]
  for:     <evidence lines>
  against: <evidence lines>
  kill:    <observation that would kill this>

H2 ...

PROBE LOG:
  P1 <what was run> -> predicted: H1=<x> H2=<y> ... -> observed: <z> -> effect: <kills/updates>
```

Update it after every probe, before choosing the next one. The probe log's "predicted before observed" ordering is the anchoring guard in physical form.

## Heuristics

- Keep 2-4 live hypotheses; 1 is anchoring, 5+ means your symptom statement is too vague — sharpen it first.
- If you have held a single hypothesis for 3+ probes without a kill or confirm, stop and generate rivals before probing again.
- Best probe ≈ the one where you genuinely cannot predict the outcome; if you're certain what it will show, it discriminates nothing.
- One cheap probe that kills two hypotheses beats an expensive probe that confirms one — prefer disconfirmation per minute.
- Always keep one "boring" hypothesis alive: stale build, wrong environment, bad test data, misread symptom. It wins embarrassingly often and is cheapest to kill.
- Time-box hypothesis generation to ~5 minutes / one written table; the value is in probing, not brainstorming.
- Evidence that surprises you is worth 10x evidence that confirms you — log every surprise in the table even if it fits no current hypothesis.
- A resurrected hypothesis re-enters with its old evidence intact; re-examine whether its kill evidence was actually decisive or merely suggestive.
- If two probes are equally discriminating, run the faster/cheaper one; iteration count beats probe elegance.
- Bisection (git bisect, binary chop over inputs/config) is the highest-discrimination probe family when hypotheses map to "before vs after" or "with vs without" — reach for it before instrumenting.
- When the live set hits zero, the fault is in step 1: the symptom statement smuggled in a false assumption. Re-verify the symptom itself (reproduce it yourself) before generating a new set.
- Never let one probe both kill a hypothesis and confirm another on ambiguous evidence; a reading that "kind of" fits both directions decides nothing — record it in both against/for columns and design a sharper probe.
- Cost-rank probes: reading existing logs < flipping a flag < adding a log line < writing a repro < attaching a profiler < rebuilding the environment. Exhaust each tier's discrimination before paying for the next.

## Anti-patterns

- **Anchoring on the first plausible cause.** You read the code, spot something suspicious, and spend an hour "confirming" it. → Corrective: before the first probe, force-write two rivals from different categories (data, config, environment) and give all three kill criteria.
- **Confirmation probing.** Every probe you pick would strengthen the favorite; none could kill it. → Corrective: for each probe, write what outcome would kill the leader; if no outcome could, pick a different probe.
- **Zombie hypotheses.** A hypothesis met its kill criterion but you keep "just checking one more thing" on it. → Corrective: kills are mechanical; mark DEAD with the evidence line and move budget to the live set.
- **Silent hypothesis mutation.** Contradicting evidence arrives and you quietly reshape the favorite ("well, it's not the pool size, it's the pool *timeout*...") without recording the shift. → Corrective: a mutated hypothesis is a NEW hypothesis — write it as H-next with fresh kill criteria and let the old one die on the record.
- **Untracked evidence.** Findings live in your head; three probes later you cannot recall which observation ruled out what. → Corrective: maintain the written table (a scratch file or comment block); update it after every probe, before choosing the next one.
- **Premature victory.** The last hypothesis standing is declared the cause because its rivals died, not because it survived a direct falsification attempt. → Corrective: design one probe whose purpose is to break the survivor; only fix after it holds.

## Worked example

*Illustrative construction, not a recorded run.*

Symptom (step 1): API p99 latency spikes to 8s every ~10 minutes under steady 200 rps; p50 unaffected.

Agent writes the table (steps 2-4):

- H1: GC pauses — JVM full GC on old-gen pressure stalls all requests.
  Kill: GC log shows no pause >500ms aligned with spikes.
- H2: DB connection pool exhaustion — a slow query holds connections; tail requests queue.
  Kill: pool metrics show free connections available during a spike.
- H3: Cron-triggered cache eviction — thundering herd on refill every 10 min.
  Kill: spike timestamps do not align with the cron schedule (or spikes persist with cron disabled).
- H4 (boring): monitoring artifact — the p99 aggregation itself is wrong; no user impact.
  Kill: raw access logs show the same 8s tail.

Note: H1 initially had an empty "against" column — it was the agent's first instinct from
seeing a Java service. That emptiness is flagged as anchoring risk, not evidence.

Probe P1 (step 5): overlay spike timestamps on the cron schedule.
Chosen because it splits H3 from {H1, H2, H4} at zero cost (reading two logs); attaching a
profiler now would only inform H1 — the anchored favorite — and discriminate nothing else.

Predictions committed first (step 6): H3 → exact alignment with the */10 cron;
H1/H2/H4 → no particular alignment.
Observed: spikes at :07/:17/:27; cron fires at :00/:10/:20. No alignment.
Effect (step 7): H3 DEAD (kill met via schedule mismatch — cheaper than disabling the job).
Residue logged: the clean ~10-minute period is now evidence explained by NO live hypothesis.
Recorded as a surprise; the surviving mechanism must eventually account for it.

Probe P2: pull GC logs AND pool metrics for one spike window — one probe testing two kill
criteria simultaneously (H1 vs H2 discrimination), plus raw access logs for H4.
Predictions: H1 → full-GC pause ≥ spike duration; H2 → free connections hit 0; H4 → raw logs clean.
Observed: max GC pause 120ms (H1 DEAD); pool at 0 free connections for 6s during the spike
(H2 for-column grows); raw logs show real 8s responses (H4 DEAD).

Falsification pass on the survivor (step 8): agent attacks H2 rather than declaring victory —
"if pool exhaustion is the mechanism, the slow-query log must show a specific query starting
at each spike, and it must also explain the 10-minute period H3 failed to claim."
Observed: a 5s analytics query fires at :07/:17/:27, driven by a client-side 10-minute poll
offset from the cron. Survivor holds AND absorbs the orphaned period evidence.

Fix + evidence walk (step 9): move the analytics query to a replica, add a pool checkout
timeout. Re-walk the table: period (client poll), tail-only impact (queueing, not stall),
pool saturation, GC innocence — every recorded observation consistent. No unexplained
residue, so no resurrection (step 10) needed. Had the spikes persisted, the agent would have
re-opened H3 first, since its kill relied on schedule alignment, the weakest evidence taken.

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
