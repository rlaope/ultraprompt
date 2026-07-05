---
name: failure-mode-enumeration
description: Systematically enumerate how code can break — boundaries, concurrency, partial failure, malicious input, time, resource exhaustion — before writing defenses, then convert the list into tests and guards while pruning paranoia that does not pay rent.
---
# Failure-Mode Enumeration

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- Writing any code that crosses a trust or process boundary: network calls, disk I/O, user input, IPC, subprocess spawning.
- Designing a system where partial failure is possible: queues, retries, distributed transactions, multi-step writes.
- Implementing a parser, protocol handler, or format decoder that will receive arbitrary bytes.
- Adding concurrency: shared state, locks, async cancellation, anything with more than one thread of execution.
- Reviewing code before shipping when the cost of a production failure is high (payments, data loss, security).
- The user asks "what could go wrong here?" or wants tests hardened against edge cases.

## Core loop

1. **Fix the unit of analysis first.** Name the exact function, endpoint, or state machine you are enumerating against.
   Enumerating "the system" produces vague worry; enumerating `consume_message()` produces a checklist.
   Write the unit's contract in one line: inputs, outputs, and the invariants that must hold after it runs.
2. **Run the standard failure taxonomy against it, category by category.** Do not brainstorm freely — walk the fixed list so nothing is skipped:
   - **Boundary values**: zero, one, max, max+1, negative, empty string/list/map, exactly-at-limit.
   - **Huge inputs**: 10^6x the expected size — does memory, latency, or a downstream limit blow up first?
   - **Malformed/malicious input**: wrong type, truncated bytes, injection payloads, adversarially crafted values
     (lengths that overflow, names that collide, nesting that recurses).
   - **Concurrency interleavings**: two callers at once; read-modify-write races; check-then-act gaps;
     reentrancy; cancellation arriving mid-operation.
   - **Partial failure**: a network call succeeds but the response is lost; a disk write half-completes;
     the process dies between step 2 and step 3 of a 3-step operation; a downstream returns 500 after
     the side effect already committed.
   - **Time**: clock skew between machines, DST transitions, leap seconds, events arriving out of order,
     timeouts firing during success, retries after the original eventually succeeded.
   - **Resource exhaustion**: connection pool empty, file descriptors gone, disk full, OOM,
     thread pool saturated, queue growing without bound.
3. **Run the pre-mortem.** Ask: "It is 3 months from now and this component caused an incident.
   What is the postmortem's root cause?" Write the 2-3 most plausible answers before continuing.
   This surfaces systemic failures — config drift, a dependency upgrade, 10x load growth — that the
   taxonomy's input-level sweep misses.
4. **Classify each enumerated mode by blast radius**:
   (a) wrong answer returned silently, (b) crash or error surfaced loudly,
   (c) data corrupted or lost, (d) resource leaked slowly.
   Silent-wrong-answer and corruption modes get priority; loud crashes are already half-defended
   because someone will notice them.
5. **Price each mode: likelihood × blast radius × cost to defend.**
   Kill the modes that fail this test explicitly — write "not defending against X because Y"
   in a comment or design note. Paranoia that does not pay rent becomes code that other people
   must read, maintain, and debug false positives from.
6. **Convert every survivor into a concrete artifact**:
   a test that reproduces the failure (kill -9 mid-write, inject the 0-length input, spawn two concurrent callers),
   OR a guard in code (timeout, size bound, idempotency key, checksum),
   OR both for corruption-class modes.
   An enumerated mode with no test and no guard is a wish, not a defense.
7. **Verify each guard by triggering the failure it defends against.**
   A guard that has never fired is unverified. Force the pool to exhaust, feed the truncated bytes,
   kill the process at the marked line. If a mode genuinely cannot be triggered in a test environment,
   downgrade your confidence in that guard and say so in the report.
8. **Re-run steps 2-3 after implementation.** The code you actually wrote has failure modes the design
   did not: a new allocation, a new lock, a new syscall, new retry state. Diff the final code against
   the original enumeration and add the modes the implementation introduced.

## Heuristics

- Every `await`, network call, and disk write is a point where the process can die: ask "what state is left if we stop exactly here?" at each one.
- If an operation has N steps with side effects, there are N+1 crash points; the operation must be idempotent or resumable, or it will corrupt state eventually.
- Any check-then-act sequence (`if exists: update`) is a race unless the check and the act are atomic — assume two callers hit the gap on day one of real traffic.
- Empty collection, single element, and exactly-at-capacity find more bugs per minute than random fuzzing; test those three before anything else.
- Retries turn one failure mode into two: the original failure, and the duplicate side effect when the "failed" call actually succeeded. Never add a retry without an idempotency story.
- If a queue, buffer, or cache has no explicit size bound, its bound is total process memory — write the bound or accept the OOM.
- Every timeout must be shorter than the caller's timeout, or the caller gives up first and your result is delivered to nobody.
- Pruning budget rule: if the failure requires 2+ independent rare events AND its blast radius is loud-crash (not corruption), skip the guard and leave a comment instead.
- Timestamps from different machines are not ordered; if correctness depends on order, use a logical clock or a single writer.
- When input comes from outside the process, validate at the boundary once and pass typed/parsed values inward — do not re-validate at every layer.

## Anti-patterns

- **Defense before enumeration.** Sprinkling null checks and try/catch while writing code, without a systematic list —
  produces uneven armor: triple-checked trivia next to unguarded corruption paths.
  → Corrective: enumerate first against the fixed taxonomy, then defend the priced list.
- **Happy-path tests labeled as edge-case tests.** Testing "empty input returns empty output" but never
  "process dies between WAL append and index update."
  → Corrective: for each corruption-class mode, write the test that actually induces the failure
  (fault injection, kill -9, concurrent load), not a test adjacent to it.
- **Uniform paranoia.** Guarding a local CLI tool's config parser as hard as a public API's request parser.
  Defenses have carrying cost — reading, maintaining, and false-positive firing.
  → Corrective: price every mode (step 5), delete guards for modes you explicitly declined, record the decision.
- **Catch-and-continue as a defense.** Wrapping the whole operation in a broad exception handler that logs
  and proceeds converts loud crashes into silent wrong answers — the worst blast-radius class.
  → Corrective: handle only the specific modes you enumerated; let everything else crash loudly.
- **Enumerating inputs but not time and interleavings.** Input-space sweeps feel complete but miss the races
  and ordering bugs that dominate production incidents.
  → Corrective: the concurrency, partial-failure, and time categories are mandatory passes, not optional extras.
- **The list that never becomes code.** A thorough failure-mode document with zero corresponding tests or guards.
  → Corrective: step 6 is the deliverable — each surviving mode maps to a named test or a named guard, one-to-one.

## Worked example

*Illustrative construction, not a recorded run.*

Task: implement a message-queue consumer with retry and DLQ.

- Agent fixes the unit: `consume(msg) -> ack|nack`, invariant: "every message is processed at least once
  and side effects are not duplicated on redelivery."
- Agent walks the taxonomy against `consume`:
  - Boundary: 0-byte body; body exactly at the broker's max frame size.
  - Huge: 50MB body when the handler assumes JSON fits in memory.
  - Malformed/malicious: non-UTF8 bytes; valid JSON with wrong schema; a poison message that
    deterministically crashes the handler.
  - Interleavings: broker redelivers while the first delivery is still processing
    (visibility timeout shorter than handler runtime).
  - Partial failure: handler writes to DB, then the process dies before ack → redelivery duplicates the DB write.
  - Time: retry backoff timer fires during a broker reconnect; messages processed out of order after redelivery.
  - Exhaustion: unbounded in-flight prefetch fills memory when the downstream DB slows.
- Agent runs the pre-mortem: "3 months later, incident: one poison message crash-looped the consumer,
  queue backed up 6 hours." Second answer: "duplicate payment rows after a deploy killed pods mid-ack."
- Agent classifies: duplicate-DB-write and poison-crash-loop are corruption/availability class → priority.
  Non-UTF8 body is loud-crash class and cheap to guard → keep.
  Leap-second handling → priced out; comment written: "not defending; broker timestamps unused for ordering."
- Agent converts survivors:
  - Idempotency key on the DB write (guard) + a test that delivers the same message twice.
  - Retry counter with DLQ routing after 3 attempts (guard) + a test injecting a handler that always throws.
  - Prefetch bound of 32 (guard) + a test with a 10-second-sleep handler asserting memory stays flat.
- Agent verifies by triggering: runs the duplicate-delivery test; kills the consumer with SIGKILL between
  the DB commit and the ack; observes redelivery; asserts exactly one row exists.
  The poison test shows the message lands in the DLQ on attempt 4.
- Post-implementation re-sweep: the retry counter itself is new state — where does it live if the process dies?
  Agent observes it was in-memory → moves it into the message header (broker-side), closing a mode
  the design phase could not have seen because the counter did not exist yet.

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
