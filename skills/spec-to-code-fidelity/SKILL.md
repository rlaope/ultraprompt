---
name: spec-to-code-fidelity
description: Invoke when implementing from an authoritative written source — an RFC, academic paper, binary format spec, protocol document, or mathematical derivation — where correctness means matching the document, not just passing ad-hoc tests.
---
# Spec-to-Code Fidelity

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- Implementing a protocol or format from an RFC, W3C/WHATWG spec, or vendor format document (HTTP/1.1, WebSocket framing, GGUF, JWT, WAI-ARIA).
- Translating equations from a paper into code (attention math, quantization schemes, PPO loss, numerical integrators).
- Writing a parser/serializer for a binary or wire format where a single off-by-one silently corrupts everything downstream.
- Porting a reference implementation to another language while claiming behavioral equivalence.
- Any task where the acceptance criterion is "conforms to the document" rather than "seems to work."
- Debugging interop failures where your implementation and a peer disagree about what the spec says.

## Core loop

1. **Acquire the authoritative text before writing code.** Get the actual RFC/paper/spec section into context — not your memory of it. If the exact document version matters (RFC obsoleted-by chains, paper v1 vs v2 on arXiv), pin the version and record it in a comment at the top of the implementation.
2. **Decompose the spec into a numbered clause inventory.** Walk the document and list every normative statement (MUST/SHALL/SHOULD, every equation, every field of every struct/frame, every state transition). Give each clause a stable ID (e.g. `§5.2-3`, `Eq.4`). This inventory is your requirements list and later your test matrix.
3. **Adopt the spec's vocabulary in code.** Name identifiers, types, and constants exactly as the spec names them (`opcode`, `masking_key`, `d_model`, `scale`/`zero_point`), even when the spec's names feel awkward. Cite clause IDs in comments next to the code that implements them. A reader holding the spec must be able to diff document against code by eye.
4. **Implement clause-by-clause, marking coverage.** For each clause: implement it, tag it `[done]`, `[deviates: reason]`, or `[ambiguous: interpretation chosen]`. Never let a clause silently fall into "probably handled." Deviations and ambiguity resolutions go in a `SPEC_NOTES` section (file header or separate doc) — this is the artifact interop debuggers will need.
5. **Extract every worked example and test vector from the spec first.** RFCs carry example exchanges; papers carry example tables and reported figures; format specs carry sample hex dumps. Turn each into an executable test *before or during* implementation — these are the only tests whose expected values you didn't invent. Concrete artifacts: a `vectors/` fixture directory holding the bytes or values verbatim from the document, and one test per vector named after its clause ID (`test_5_7_masked_hello`) so a failing test names the clause it violates.
6. **Cross-check against a reference implementation or oracle where one exists.** Run the canonical implementation (curl for HTTP, jwt.io vectors, the paper authors' repo, llama.cpp for GGUF) on the same inputs and diff outputs byte-for-byte or number-for-number. Make the diff a committed script (`scripts/oracle_diff.sh`), not a one-off shell session — you will re-run it after every substantive change and once more at the final audit. Where no oracle exists, hand-compute at least one small case on paper and commit it as a fixture, with the derivation recorded in a comment next to the expected values.
7. **Validate numerics against known values before trusting downstream behavior.** For math-heavy specs: check intermediate quantities (attention weights sum to 1, quantize→dequantize round-trip error within the scheme's stated bound, loss at init ≈ ln(vocab_size)) against analytically known values. Encode these as assertions or a standalone sanity-check entry point that prints each invariant with its observed value, so the check re-runs for free on every future change. A converging loss curve or a "working" demo is not evidence the math is right — many wrong implementations still converge or interoperate by accident.
8. **Audit clause coverage before declaring done.** Sweep the clause inventory: every clause is `[done]`, `[deviates]`, or `[ambiguous]` with a test or a note. List untested clauses explicitly in the final report. "All tests pass" is meaningless if the tests cover 30 of 80 clauses.
9. **Re-read the spec once more after implementation.** A final pass with working code in hand catches misreadings that were invisible on first read — you now know which sentences you skimmed. Budget this pass; it is where the subtle bugs (network byte order, inclusive vs exclusive ranges, 0- vs 1-indexed equations) surface. Exit: every clause accounted for, spec vectors green, oracle diff (or hand-computed fixture) green.

## The clause inventory artifact

Maintain the inventory as a literal artifact — a `SPEC_NOTES` block in the file header or a sibling doc, not working memory:

```
SPEC: RFC 6455 (no errata relevant to §5.2), fetched <date>
CLAUSES:
  §5.2-1  FIN/RSV/opcode bit layout            [done]  test_5_2_bits
  §5.2-2  7/16/64-bit payload length encoding  [done]  test_5_2_len16, test_5_2_len64
  §5.3-1  masking algorithm: j = i MOD 4       [done]  test_5_7_masked_hello
  §5.5-1  control frames ≤125B, unfragmented   [deviates: also reject close frames
          whose reason is invalid UTF-8 — stricter than the spec requires]
  §5.5.1  reserved close status codes          [ambiguous: spec silent on 1015 when
          received; chose: treat as protocol error, matching browser behavior]
UNTESTED: §5.5.1 reserved codes — reported explicitly, low interop risk
```

Rules for the artifact:

- One row per clause; the coverage tag and its test name (or note) live on the same line, so `grep '\[deviates'` produces the complete deviation report in one command.
- Rows are retagged, never deleted, once implementation starts — a deleted row is a clause you forgot, not a clause you resolved.
- The audit in step 8 is a mechanical sweep of this block, not a re-read of the code; if the sweep requires judgment, the tags were written too loosely.

## Heuristics

- If the spec gives a worked example, implement enough to reproduce that exact example before anything else — it is the cheapest full-pipeline test you will ever get.
- MUST/SHALL clauses each get a test; SHOULD clauses each get a test or a one-line documented decision to skip.
- When the spec is ambiguous, do not average interpretations: pick one, write down why, and check what the dominant reference implementation does — interop reality usually trumps a literal reading.
- Hand-compute vs oracle rule: if a runnable oracle exists and executes in under a minute, diff against it at every milestone; if the only oracle is expensive (a training run, a remote peer, special hardware), hand-compute one case small enough to verify on paper (≤ ~20 arithmetic steps) and pin it as a fixture before building anything on top.
- When porting a reference implementation, port its test suite before writing your own tests; a port that cannot pass upstream's tests is not equivalent, whatever your own tests say.
- Never copy a magic constant from another implementation without locating it in the spec; if it is not in the document, it is a deviation and belongs in SPEC_NOTES with its source named.
- Any identifier renamed away from spec terminology costs you a mapping table; if you must rename, keep an explicit `spec name → code name` table in SPEC_NOTES.
- In binary formats, verify field offsets with a hex dump of a real file before writing the parser loop — one wrong `struct` size shifts every subsequent field.
- For equations: transcribe the formula verbatim into a comment above the code, including index ranges and summation bounds; most math bugs are bound/index errors, not operator errors.
- Numeric tolerance for cross-checks: bitwise-exact for integer/serialization specs; for floating point, assert against the spec's reported figures at their printed precision, and treat >1 ULP-scale drift in a supposedly deterministic step as a bug until explained.
- If your output disagrees with the oracle, assume you are wrong first; only claim an oracle bug after you can quote the exact clause the oracle violates.
- Endianness, sign-extension, padding, and inclusive/exclusive boundaries account for a disproportionate share of spec bugs — grep your own diff for byte-order and range operations during the final re-read.
- Budget the final re-read at roughly 10% of implementation time; skipping it trades a fixed small cost for open-ended interop debugging later.

## Anti-patterns

- **Implementing from memory of the spec.** Training-data recall of an RFC blends versions and errata. → Corrective: load the actual text; quote clauses into comments as you implement them.
- **Paraphrase drift in identifiers.** Renaming `nonce` to `randomToken` "for clarity" breaks the eye-diff between doc and code and hides misunderstandings. → Corrective: keep spec terms verbatim; put clarity in comments, not names.
- **Testing only self-invented cases.** If you wrote both the code and the expected values, a shared misreading passes green. → Corrective: prioritize spec-provided vectors and oracle diffs; your own cases are supplementary.
- **Validating math by downstream behavior.** "The model trains" or "the peer accepts my handshake" can be true of subtly wrong implementations. → Corrective: assert intermediate values against known constants before running end-to-end.
- **Silently resolving ambiguity.** Choosing an interpretation without recording it makes the eventual interop bug undiagnosable. → Corrective: every ambiguity gets a SPEC_NOTES entry with the chosen reading and the alternative.
- **Declaring done on green tests without a clause audit.** Coverage of the test suite is not coverage of the spec. → Corrective: sweep the numbered clause inventory and report the untested remainder explicitly.

## Worked example

*Illustrative construction, not a recorded run.*

Task: implement WebSocket frame parsing (RFC 6455 §5).

```
Agent fetches RFC 6455 §5 and checks the errata index → pins "RFC 6455, no
errata relevant to §5.2" in the file header, because implementing from memory
blends this frame layout with other protocols' habits.
Agent walks §5.2-§5.5 → emits a 14-clause inventory: FIN/RSV/opcode bits
(§5.2), payload length 7/16/64-bit encoding (§5.2), MASK bit + masking
algorithm (§5.3), control frames ≤125 bytes and never fragmented (§5.5),
close status codes (§5.5.1).
Agent declares struct Frame { fin, rsv1..3, opcode, mask, payload_len,
masking_key, payload } → field names verbatim from the spec figure, each
commented with its clause ID, because the doc-to-code eye-diff must work.
Agent extracts §5.7's worked examples ("Hello" unmasked = 0x81 0x05 0x48...,
masked "Hello", 256-byte binary) into vectors/ and writes one test per vector
before the decoder exists → the only expected values the author didn't invent.
First run: unmasked "Hello" passes; masked "Hello" decodes to garbage.
Agent re-reads §5.3 instead of debugging the code first → because when code
and spec disagree, the cheapest probe is the four lines of normative text.
Observation: §5.3 indexes the key as j = i MOD 4; the code applied the key
bytes in reverse order — a memory-of-spec habit from a different protocol.
Fix → all spec vectors green.
Agent cross-checks the oracle: pipes 50 random payloads from a real client
(websocat) through the parser and byte-diffs against the library the client
trusts → zero diffs; the diff script is committed for re-use at audit time.
Clause audit: 12/14 tested. §5.4 fragmentation reassembly and §5.5.1 reserved
status codes are [done, untested] → fragmentation is a MUST, so two tests are
added; reserved codes stay untested and are reported explicitly.
Final re-read of §5.2 with working code in hand → 16-bit extended length
("in network byte order") is handled, but the 64-bit branch had a host-order
read on one path. Fixed before any peer ever sent a frame that large.
Exit: 14/14 clauses accounted for; spec vectors, oracle diff, and clause
audit all green.
```

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
