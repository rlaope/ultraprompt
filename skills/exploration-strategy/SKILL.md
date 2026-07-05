---
name: exploration-strategy
description: Build an accurate mental model of an unfamiliar codebase or problem before making any edit — structural scan, entry-point location, one end-to-end trace, and an explicit known-vs-assumed ledger.
---
# Exploration Strategy

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- You are dropped into a repository you have never seen and asked to change or fix something in it.
- A task description references symbols, modules, or behaviors you cannot yet locate in the code.
- You are about to edit code whose callers, config sources, or side effects you have not confirmed.
- A bug report describes a symptom but you do not yet know which layer produces it.
- Your context was compacted or the session resumed, and your prior map of the codebase may be stale.
- You catch yourself editing based on what a file "probably" contains rather than what you read.

## Core loop

1. **Restate the task as a location question.**
   Before any file read, write one sentence: "To do X, I need to find where Y happens
   and what touches it." This defines the exploration target; every subsequent read is
   judged against it. If you cannot phrase the target, the task itself is underspecified —
   resolve that first.

2. **Breadth-first structural scan (hard cap: ~10 tool calls).**
   List the top-level directory tree. Read the manifest (`package.json` / `Cargo.toml` /
   `go.mod` / `pyproject.toml` / `Makefile`) and the README headings only.
   Output for yourself: language, build system, test command, and 3-6 candidate
   directories relevant to the task. Do not open individual source files yet.

3. **Locate entry points.**
   Find where execution starts for the behavior in question: `main`, HTTP route tables,
   CLI arg parsers, event handlers, exported public API, scheduled jobs.
   Grep for the task's key nouns first — error strings, endpoint paths, flag names,
   config keys. Literal strings lifted from the task description are the highest-signal
   search keys available: near-zero false positives.

4. **Trace ONE representative path end-to-end.**
   Pick the single most task-relevant flow and follow it from entry point to observable
   effect (response written, file persisted, state mutated), reading only files on that
   path. Depth-first on one path beats shallow reads of ten files: the traced path
   reveals the layering conventions, error-handling style, and data shapes that
   generalize to the rest of the codebase.

5. **Maintain a known/assumed ledger.**
   As you trace, keep two explicit lists:
   - KNOWN — facts confirmed by reading code or running commands, each with a
     file:line or command receipt.
   - ASSUMED — inferences from names, docs, comments, or convention.
   Every ASSUMED item is a liability. Promote it to KNOWN by reading the code, or
   carry it into the plan as a named risk. Never let an assumption become load-bearing
   silently.

6. **Probe dynamically if cheap.**
   If the project runs or tests in one command, run it once before editing. One observed
   runtime behavior — a log line, a passing suite, a reproduced error — outweighs ten
   inferred ones, and it validates the build/verify loop before you depend on it.

7. **Apply the sufficiency test.**
   Stop exploring when you can answer all four:
   - (a) Where exactly will my edit go?
   - (b) What calls into it, and what does it call?
   - (c) How will I verify the change worked?
   - (d) What is the most likely way my change breaks something else?
   Four yes answers → begin editing immediately. Any no → that question names the
   next thing to read; read only that.

8. **Declare the model, then act.**
   Write a 3-6 line summary: architecture in one line, the traced path, the edit site,
   the verification plan, and the surviving ASSUMED items. This is your checkpoint —
   if an assumption later proves wrong, you know exactly which belief to revise instead
   of restarting exploration.

9. **Re-explore only on surprise.**
   During implementation, return to exploration only when reality contradicts the
   ledger (a KNOWN item was wrong, or an ASSUMED item turned out to matter).
   Fix that one entry, re-trace the minimal affected path, resume. Do not rescan the
   repository.

## Heuristics

- Read the manifest and directory tree before any source file; the build system reveals the architecture faster than the code does.
- Grep for literal strings from the task (error messages, route paths, config keys) before grepping for concept words.
- One end-to-end trace of a representative path teaches more than skimming N sibling files; siblings usually mirror the traced one's structure.
- Time-box the structural scan: if step 2 hits ~10 tool calls without candidate directories, switch to keyword grep instead of browsing further.
- Exploration budget scales with blast radius, not repo size: a one-line fix in a 1M-line repo needs only the traced path around that line.
- If two consecutive reads produce no new KNOWN entries, exploration has saturated — run the sufficiency test now.
- Tests are compressed documentation: a module's test file states intended behavior and canonical call patterns; read it before the implementation when both exist.
- Never trust a function by its name alone; if your change depends on its behavior, read its body — name/behavior mismatch is a top source of wrong edits.
- Prefer one cheap runtime probe (run tests, curl the endpoint, execute the script) over three more file reads when the project boots in under a minute.
- After context compaction or session resume, re-verify the top three KNOWN items you are about to build on; stale certainty is worse than admitted ignorance.

## Anti-patterns

- **Edit-first archaeology.** Making the "obvious" change immediately, then discovering three call sites break.
  → Corrective: pass the four-question sufficiency test before the first edit; question (b) — callers and callees — is the one this failure skips.
- **Exploration as procrastination.** Reading a twentieth file "for context" when the edit site was clear ten files ago, because reading feels safer than committing to an edit.
  → Corrective: the no-new-KNOWN-in-two-reads rule; when it fires, write the model summary and start editing.
- **Breadth without depth.** Opening the first 30 lines of fifteen files and knowing the shape of nothing.
  → Corrective: pick one representative path and trace it fully to its side effect before opening any file off that path.
- **Silent assumption stacking.** Chaining "this probably validates input" → "so the bug must be downstream" without confirming the first link.
  → Corrective: every "probably" enters the ASSUMED list out loud; any assumption load-bearing for the fix gets promoted by reading the code before building on it.
- **Doc-trust over code-trust.** Building the mental model from a README or comments that no longer match the implementation.
  → Corrective: docs generate ASSUMED entries only; only code and command output generate KNOWN entries.
- **Full restart on surprise.** One wrong assumption during implementation triggers re-reading the whole subsystem from scratch.
  → Corrective: revise the single falsified ledger entry, re-trace only paths that depended on it, resume.

## Worked example

*Illustrative construction, not a recorded run.*

Task: "POST /orders sometimes returns 500 when a discount code is applied. Fix it."
Unfamiliar Node.js repo, ~40k lines.

- Agent restates the target: "Find where POST /orders handles discount codes, and what
  in that path can throw." (step 1)
- Agent lists the root tree and reads `package.json` → Express + Prisma, `npm test`
  exists. Candidate dirs: `src/routes/`, `src/services/`, `src/db/`. No source files
  opened yet. (step 2)
- Agent greps `"orders"` under `src/routes/` → `routes/orders.js` maps POST to
  `orderService.create`. Greps `discount` → `services/discount.js`, `services/order.js`.
  Entry point located in 3 tool calls. (step 3)
- Agent traces one path: `routes/orders.js` → `order.create()` → `discount.apply()` →
  Prisma write → response, reading each file on the path fully. Observes
  `discount.apply()` calls `code.toUpperCase()` on the raw request field with no
  null guard. (step 4)
- Ledger. KNOWN: route wiring (`routes/orders.js:24`); `apply()` dereferences `code`
  unguarded (`services/discount.js:11`); error middleware converts any throw into a
  500 (`middleware/errors.js:8`). ASSUMED: clients sometimes omit `code`; no upstream
  validation layer strips or defaults the field. (step 5)
- Agent promotes the assumption because the fix depends on it: greps for validation
  middleware on the orders route → none registered. Runs `npm test` — green, so the
  test loop works. Reproduces with `curl -d '{"items":[...]}'` → 500 with
  `TypeError: Cannot read properties of undefined (reading 'toUpperCase')`.
  The assumption becomes KNOWN via runtime evidence. (steps 5-6)
- Sufficiency test: edit site known (`discount.js:11`); callers/callees known (only
  `order.create` calls it; it only reads the codes table); verification known (rerun
  the curl repro, add a regression test); blast radius known (single call site).
  Four yes → exploration stops. (step 7)
- Agent declares the model in 4 lines, adds a guard returning 400 for missing/unknown
  codes, adds a test for the no-code case, reruns curl → 400, `npm test` → green.
  Total exploration: ~9 tool calls, one path traced end-to-end, zero unrelated files
  read. (steps 8-9)

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
