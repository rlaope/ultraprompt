# Simulation & Distillation Protocol

How a new strategy axis becomes a skill. Read this before authoring any `skills/<new-axis>/`.

A skill is not written from intuition. It is *distilled* from a real Claude Fable 5.1 session run on a
representative task, so that every heuristic in it can eventually point back to a trace that produced it.
This document is the protocol; `_TEMPLATE.md` is the shape the output must take.

## The 5-step protocol

1. **Pick a representative task in a NEW domain.**
   Choose a task the candidate axis should govern, in a domain *unlike* the ones the existing axes were
   drawn from (so the pattern is forced to transfer, not memorize). One concrete task, real stakes, a
   clear success signal. Write down which candidate axis you expect it to exercise before you run it.

2. **Run a real Fable 5.1 session on it.**
   Actually execute the task with Fable 5.1 — not a thought experiment, not a paraphrase. Let the model
   work end to end. The session is the primary source; everything downstream is derived from it.

3. **Capture the reasoning trace.**
   Record the event trace: what the agent observed, what it decided, where it corrected, what it verified.
   Store it as case evidence. The trace — not your recollection of it — is what a `CASES.md` row cites.

4. **Distill the strategy axis (strategy, not domain).**
   Extract the repeating decision pattern and name it as a *strategy* that transfers across domains, never
   as a domain skill. "Hypothesis Management", not "Debugging Python". If the pattern only makes sense in
   the task's domain, it is not an axis — it is an example. A real axis shows the same shape in at least
   two unrelated domains.

5. **Author `SKILL.md` (per `_TEMPLATE.md`) + append a `CASES.md` evidence row.**
   Write the skill in the template's fixed section order (When to apply / Core loop / Heuristics /
   Anti-patterns / Worked example / Trace evidence), 120–220 lines, English. Then append one row to that
   skill's `CASES.md` naming the session and which section the trace confirmed, contradicted, or refined.
   The skill and its evidence are authored together, side by side, in this repo.

## Quality bar

- Every new skill is born as a draft. Its status line reads, verbatim:
  `> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5.1 case runs.`
- **Promotion to final requires ≥1 real trace-evidence row in the skill's `CASES.md`.** No trace, no promotion.
  Until then the draft marker stays and the version stays `v0.1`.
- Trace rows are recorded from real runs only. Never invent a row; never write "final" from intuition.
  The worked example in a draft is an *illustrative construction* (marked as such) until a trace replaces it.

## Distinctness rule

- A candidate axis must earn its place by showing trace evidence **distinct from every existing axis** —
  the core eight (exploration-strategy, hypothesis-management, verification-discipline, tradeoff-articulation,
  failure-mode-enumeration, self-correction-loop, spec-to-code-fidelity, incremental-safety) and the current
  drafts (state-probing, honest-reporting, delegation-parallelism, context-memory-hygiene).
- If the candidate's trace cannot be distinguished from an existing axis — the same decisions would fire
  under an existing skill — it is **ABSORBED into the nearest existing axis, not shipped**. No duplicate axes.
- Each new skill carries a short "Relation to existing axes" note stating the one boundary that makes it
  distinct (e.g. "exploration builds a model of the CODE; state-probing grounds claims about the RUNTIME").
  That note is a promise the trace evidence must later keep.

## Cap discipline

- New axes must be loadable by a router: an orchestrator (Claude Code's skill loader, or any agent harness
  that reads frontmatter) decides from the `description` line alone whether to load the skill. Every new skill therefore needs **router-ready trigger lines** — a `description`
  that names the conditions under which it should be loaded, phrased for a router, not a human reader.
- The axis count is a budget, not a free list. A new axis is added only when it is genuinely distinct
  (see above) and its triggers do not overlap an existing skill's triggers. Prefer absorbing over adding.

## Provenance rule

- This repository (`rlaope/ultraprompt`) is the **publishing home**: the canonical, installable set of skills.
  The **authoring working copy** is [maestro-ultra](https://github.com/animepics/maestro-ultra), where the
  conductor exercises the skills on real sessions and where a skill and its `CASES.md` rows are drafted side
  by side.
- Skills flow **from the working copy up to this repo**, eventually-consistent, with a provenance line in both
  directions:
  - working-copy side → `Published upstream to rlaope/ultraprompt @ <sha>`
  - this repo → the `Provenance:` line at the top of each skill's `CASES.md`
- **Never author the same skill twice.** One authoring source, one publishing mirror. A skill re-drafted
  independently on both sides splits the source of truth; fix the drift by re-mirroring, not by merging prose.
- The mirror push is an owner-approval gate: drafting is autonomous; landing a skill here waits for the
  maintainer's review (a pull request against `main`).
- Every change landing here must pass `scripts/validate-skills.sh` (run in CI): frontmatter, section order,
  status line, line budget, and a `CASES.md` next to every `SKILL.md`.
