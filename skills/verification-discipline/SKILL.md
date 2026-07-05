---
name: verification-discipline
description: Invoke before claiming any task is done — defines what counts as evidence of completion (execution, not inspection) and how to verify at the layer the requirement actually lives at.
---
# Verification Discipline

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- You are about to say "done", "fixed", "implemented", or "this should work" in any form.
- You wrote or changed code but have not yet executed the changed path.
- The requirement is stated in terms of runtime behavior: performance, concurrency, crash recovery,
  rendering, protocol compliance, or a user-visible flow.
- A bug fix exists but the original failure has not been re-triggered against the fixed code.
- Tests pass, but the requirement lives above the unit level
  (e.g., "the page loads fast", "no duplicate charge under load").
- You feel confident from reading the code alone. That feeling is the trigger, not the evidence.

## Core loop

1. **State the completion claim as an observable.**
   Before verifying anything, write down what "done" means as something the world can show you:
   "GET /orders returns 200 with the new field", "loss decreases for 500 steps",
   "the shell survives `kill -9` of a child process".
   If you cannot phrase the claim as an observation, the requirement is not yet understood — go pin it down first.
2. **Identify the layer the requirement lives at, and verify at that layer.**
   - User-visible behavior → drive the UI or hit the API end-to-end.
   - Throughput / latency → benchmark under representative load, not a single request.
   - Durability / crash safety → actually crash the process and restart it.
   - Algorithm correctness → property tests or adversarial inputs, not one example.
   A unit test only closes a unit-level claim. Never let it close a claim from a higher layer.
3. **Choose the strongest evidence tier you can afford.** In descending strength:
   - (a) reproduction of the original failing scenario, now passing;
   - (b) end-to-end execution of the real flow with observed output;
   - (c) integration test exercising the changed path;
   - (d) unit test of the changed logic;
   - (e) type-check / lint / build success.
   Tier (e) alone never supports a completion claim; it only supports "it compiles".
4. **Run the actual thing.**
   Execute the command, start the server, send the request, render the page, launch the training run.
   Capture real output — exit codes, response bodies, timings, screenshots, log lines.
   Quote or reference the observed output, never a paraphrase of what it should be.
5. **For bug fixes: reproduce first, then confirm the flip.**
   Demonstrate the failure on the pre-fix code (or a minimal repro), apply the fix,
   re-run the identical repro, and show the state change fail → pass.
   A fix without a reproduction is a hypothesis, not a fix, and must be reported as one.
6. **Probe the boundary, not just the happy path.**
   Run at least one input at the edge of the claim: empty input, concurrent access,
   the rotation/truncation case, the retry path, the largest realistic size.
   One happy-path run verifies existence, not correctness.
7. **Check for negative side effects.**
   Re-run the existing test suite, or the adjacent flows sharing code with your change.
   "My new thing works" and "I broke nothing else" are separate claims needing separate evidence.
8. **Report exactly what you observed, including the gaps.**
   State the evidence tier reached ("verified end-to-end", "unit-tested only, no load test run")
   and enumerate what remains unverified.
   If verification failed or was impossible in this environment, say so plainly and label
   the work "unverified" — never "should work".
9. **If any observation contradicts the claim, the claim is false.**
   Do not rationalize the discrepancy away, and do not soften the report to "mostly working".
   Return to the fix loop with the contradicting observation as the new failing case.

## Heuristics

- "The code looks right" has zero evidentiary weight; rank it below a passing build.
- If you never saw a code path execute, assume it has a bug; a large fraction of unexecuted new paths do.
- Match evidence scope to claim scope: a p99 latency claim needs a percentile from many requests, not one timing.
- Prefer the failing case as the permanent test fixture: the strongest regression test is the exact repro that used to fail.
- A test written after the fix must be shown to fail when the fix is reverted; otherwise it may test nothing.
- Benchmarks need a baseline: report before/after from the same machine and run count, never a lone "after" number.
- Flaky evidence is not evidence: if a verification run passes intermittently, the flakiness itself is the next bug.
- Concurrency claims need repetition: one clean concurrent run proves little; run the race N times (N ≥ 5) before trusting it.
- Time-box environment fights: if you cannot execute after ~15 minutes of setup attempts, stop,
  report "unverified" with the concrete blocker, and hand the user the exact verification command to run.
- Silence is not success for long-running processes: verify servers/training/consumers by positive signals
  (health endpoint, loss curve, consumed offsets), not by absence of errors in the first seconds.
- One command the user can run to see the result themselves beats three paragraphs of explanation.
- When output is visual (UI, chart, TUI), the evidence is a rendered artifact — a screenshot or dumped frame — not the CSS.

## Anti-patterns

- **Completion by inspection.** Declaring done after reading the diff and reasoning it through mentally.
  → Corrective: run the changed path and quote its actual output before writing any completion sentence.
- **Layer mismatch.** Unit tests pass, so the user-facing feature is declared working —
  though nothing ever rendered the page or hit the endpoint.
  → Corrective: add one verification at the layer where the requirement was stated;
  treat lower-layer green as necessary but insufficient.
- **Fixing without reproducing.** Patching the suspected cause and closing the bug
  without ever having seen the failure fire.
  → Corrective: build the minimal repro first; if the failure cannot be triggered,
  the diagnosis is unconfirmed and the report must say exactly that.
- **Hedged completion language.** "This should now work", "I believe this resolves it" —
  hedges that smuggle an unverified claim past the reader.
  → Corrective: replace the hedge with the precise state:
  either "verified: <observation>" or "unverified: <what blocks verification>".
- **Happy-path-only verification.** One clean run on the default input, then done —
  while the requirement was about load, concurrency, or failure handling.
  → Corrective: derive verification inputs from the requirement's stress words
  (concurrent, large, crash, retry, rotate) and run those cases.
- **Suppressing bad news.** A verification run half-failed, and the report leads with the passing half.
  → Corrective: report failures first, verbatim, with the failing command;
  a faithful failure report is a successful verification outcome, not a defeat.

## Worked example

*Illustrative construction, not a recorded run.*

Task: "Fix the double-decrement bug — two concurrent purchases of the last item both succeed."

- Agent restates the claim as an observable: with stock=1, firing 2 concurrent purchase requests
  must yield exactly one 200 and one 409, and final stock must be 0.
- Agent identifies the layer: this is a concurrency requirement, so a single-threaded unit test
  cannot close it. Evidence must come from actual concurrent execution against the real store.
- Agent reproduces first: writes a 20-line script firing 50 parallel requests at stock=10
  against the current code. Observes final stock = -7 and 17 successes over 10 items.
  Failure confirmed and quantified — this script is now the fixture.
- Agent applies the fix (`SELECT ... FOR UPDATE` around the read-decrement-write).
- Agent re-runs the identical script: 10 successes, 40 rejections, final stock = 0.
  Runs it 5 more times because race outcomes are probabilistic — all clean.
- Agent probes the boundary: stock=1 with 2 requests, and stock=0 with 1 request.
  Both behave exactly as specified.
- Agent checks side effects: row locking could hurt throughput. Benchmarks the endpoint
  before/after under the same 50-way load: p50 12ms → 14ms. Re-runs the full order-service
  test suite: green.
- Agent reports: "Verified by concurrent repro: pre-fix oversell of 17/10 reproduced;
  post-fix, 6 consecutive runs sold exactly 10/10 with final stock 0. Cost: p50 +2ms under
  50-way contention. Not verified: behavior across DB failover — repro script is at
  scripts/oversell_repro.sh if you want to run it against that setup."
- Note the shape of the final claim: every assertion is tied to an observed number,
  and the unverified remainder is named explicitly instead of hidden.

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
