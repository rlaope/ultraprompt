---
name: self-correction-loop
description: Invoke when an implementation attempt produces a failure signal (test failure, compile error, wrong output, crash, perf regression) and you must decide whether to retry, rethink, or back out — instead of hammering the same fix.
---
# Self-Correction Loop

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- A test, build, benchmark, or runtime check just failed after a change you made.
- You are about to re-run the same command after a fix and are not sure the fix addresses the *cause*, only the *message*.
- You notice you have edited the same file or function more than twice for the same failing check.
- Output is wrong but there is no error at all (silent bug: wrong numbers, flaky pass, loss not decreasing).
- A fix made one check pass but broke a different one — the failure moved instead of dying.
- You are inside an autonomous loop (CI bot, harness runner) and need explicit termination and escalation rules.

## Core loop

1. **Capture the signal verbatim before touching code.** Copy the exact error text, failing assertion, expected-vs-actual diff, or metric delta into working notes. Never work from a paraphrase of the failure — the paraphrase deletes the clue.

2. **Classify the failure into one of three tiers:**

   | Tier | Name | Definition | Typical evidence |
   |------|------|------------|------------------|
   | T1 | Mechanical | Typo, missing import, wrong arg order, off-by-one in a line you just wrote | Cause visible in the error text itself |
   | T2 | Wrong approach | Code does what you intended, but the intention can't solve the problem | Correct-looking code, structurally wrong result (wrong algorithm, wrong API contract, wrong concurrency model) |
   | T3 | Wrong problem model | Your understanding of the requirement, input data, or system behavior is false | Fixes keep failing in surprising ways; the spec in your head is the bug |

3. **Pick the response by tier, not by mood:**
   - T1 → fix inline and re-run immediately. One free retry, no ceremony.
   - T2 → stop editing. Write one sentence stating the alternative approach and why the current one is structurally unable to work. Then switch.
   - T3 → stop coding entirely. Re-read the spec, re-inspect the real input, or add an observation probe. Do not write a fix while your model of the problem is unverified.

4. **Log every attempt in one line before making it:**
   `attempt N: <hypothesis> → <change> → <result>`
   Keep this log in scratch notes or a comment block. Its purpose is to make cycling visible: if a new idea matches an old log line, that idea is banned.

5. **Enforce the loop budget.** Two similar failures at the same tier is a warning; the third forces escalation one tier up:
   - T1 → T2: "these aren't typos — the approach is wrong."
   - T2 → T3: "no approach works — my model of the problem is wrong."
   Never make a fourth attempt of the same kind.

6. **On escalation, widen the evidence before widening the edit.** Add a minimal probe from this menu, cheapest first:
   - Print or log the actual intermediate value at the suspected boundary.
   - Run the failing case in isolation (single test, single input, single request).
   - Bisect the input: does half the data still trigger it?
   - Diff behavior against a known-good reference (old commit, reference implementation, second environment).
   - Read the actual runtime state (debugger, strace, EXPLAIN, network capture) instead of inferring it from source.
   One new fact beats three new guesses.

7. **Locate the fix layer independently of the symptom layer.** Ask: "is the code that emitted this error the code that is wrong?"
   - A serializer exception is often a data-model bug.
   - A frontend render glitch is often an API-contract bug.
   - A flaky test is often a shared-state bug.
   Fix at the causing layer; at most add an assertion at the symptom layer.

8. **Decide fix-forward vs back-out explicitly.** Back out when any of these hold; otherwise fix forward:
   - The working-tree delta since the last green state is large or tangled with unrelated edits.
   - The attempt log shows ≥3 failed attempts layered on top of each other.
   - You can no longer state which of your edits are load-bearing and which are debris.
   Revert to the last known-good state and re-apply the smallest slice that reproduces the failure. Backing out is a move, not a defeat.

9. **After the fix, re-run the original failing check AND the checks that passed before.** A fix that migrates the failure elsewhere counts as attempt N+1 in the log, not as progress.

10. **Close the loop with a one-line cause statement:** "root cause: X, fixed at layer Y, guarded by check Z." If you cannot write that sentence, the failure is suppressed, not fixed — reopen.

## Heuristics

- T1 fixes get exactly one free retry; if the "typo fix" fails, it was never a typo — reclassify as T2.
- 3 similar failures = mandatory strategy change. Similar means: same error class, same file region, or same hypothesis family.
- If two consecutive fixes each broke something the previous fix had fixed, you are in a whack-a-mole cycle: back out to last green and re-derive the invariant both call sites depend on.
- A fix you cannot explain ("I moved the line and it passed") is not a fix — keep the failing check red and find the mechanism before proceeding.
- Silent wrongness (bad output, no error raised) is T3 by default: instrument first, hypothesize second, edit third.
- If the error message *changed* after your edit, that is progress even though it still fails — log it as a new failure family and reset the similar-failure counter.
- Time-box T3 investigation: if 15–20 minutes of probing yields no new fact, state the top two hypotheses explicitly and design one experiment that discriminates between them.
- When the same failure appears in multiple callers or tests, the fix almost never belongs in the callers — look one layer down for the shared dependency.
- Cheap probes before expensive rewrites: a print statement, an isolated repro, or a `git stash` A/B run each cost minutes; a speculative refactor costs hours and destroys evidence.
- In autonomous loops, hard-cap total iterations (e.g., 5) and require each iteration to change either the hypothesis or the evidence; an identical retry is grounds for termination, not repetition.
- Distinguish "my change broke it" from "it was already broken": run the failing check on the pre-change state once before debugging your diff.

## Anti-patterns

- **Brute-force retry.** Re-running the same failing command hoping for a different result, or re-applying a near-identical patch.
  → Corrective: consult the attempt log; if the idea matches a logged attempt, escalate tier instead of retrying.
- **Error-message whack-a-mole.** Patching each error as it surfaces — add a null check here, catch an exception there, widen a type — without asking why the value is wrong.
  → Corrective: trace the bad value to where it was produced; fix production, not consumption.
- **Paraphrase debugging.** Reasoning from memory of the error ("it was some kind of type error") instead of the verbatim text.
  → Corrective: re-run once, capture exact output, read it word by word — including the parts you skipped the first time.
- **Sunk-cost tunneling.** Refusing to abandon an approach because hours of edits sit on it.
  → Corrective: the attempt log is the exit ramp — if it shows the approach failing structurally, revert to last green; the knowledge survives even when the code doesn't.
- **Fix-at-symptom-layer.** Silencing the failure where it surfaced: skip the test, loosen the assertion, wrap in a retry.
  → Corrective: treat every urge to weaken a check as evidence you haven't found the cause; find the layer that produced the bad state.
- **Unbounded self-correction.** An agent loop that patches → tests → patches forever with no termination rule.
  → Corrective: define the budget, the escalation ladder, and a "stop and report blockers" terminal state *before* entering the loop.

## Worked example

*Illustrative construction, not a recorded run.*

Task: a message-queue consumer's integration test fails.

```
FAILED test_consume_batch: assert processed == 100, got 97
```

- Agent captures the verbatim output. 3 messages lost, no exception raised → silent wrongness → leans **T3**, but runs one cheap T1-level check first.
- Logs `attempt 1: off-by-one in batch slicing? → read batching code → slicing correct, hypothesis dead`.
- Two failure-free reads of the same code would be attempt cycling — so instead of re-reading, agent widens evidence: adds a probe logging message IDs at consume-time and at ack-time. Re-runs.
- Observes: the 3 missing messages *were* consumed but never acked; each threw a JSON decode error swallowed by a bare `except: continue` in the consume loop.
- Reclassifies as **T2** — the failure policy "silently skip poison messages" is the wrong approach — and notes the **layer split**: symptom lives in the test's counter assertion; cause lives in the consume loop's error handling.
- Momentary temptation: change the assertion to `processed >= 97`. Rejected — that is fix-at-symptom-layer; the assertion is correctly reporting data loss.
- Logs `attempt 2: poison messages swallowed → route decode failures to DLQ and count them → expect 97 processed + 3 dead-lettered`.
- Implements DLQ routing at the consume loop. Re-runs the failing test *and* the previously green unit suite (guarding against failure migration).
- Result: test updated to assert the new contract (97 processed, 3 in DLQ, 100 accounted for); all checks green, nothing else broke.
- Closes: "root cause: bare except discarded undecodable messages; fixed at consume-loop error policy; guarded by DLQ-count assertion."
- Loop terminates at attempt 2 of budget 5. Attempt log shows no repeated hypothesis.

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
