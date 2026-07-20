---
name: context-memory-hygiene
description: Invoke when deciding what to load into context, what to persist across turns or sessions, and what to drop — reads only what the task needs, writes durable handoffs, avoids context pollution, and chooses when to re-derive versus recall.
---
# Context & Memory Hygiene

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- You are about to read files, dump logs, or pull in references and must decide how much to actually load.
- The context window is filling and older content is at risk of being crowded out or compacted.
- A session will resume later, or hand off to another agent, and state must survive the boundary.
- You are unsure whether to trust a remembered value or re-derive it from the current source.
- You caught yourself loading a whole file/log/repo to use one function or one line from it.
- Work spans multiple sessions and you need a durable record that is not the transcript itself.

## Core loop

1. **State what the current step actually needs.**
   Before loading anything, name the specific fact, symbol, or slice the next action requires. "I need the
   signature of `parseConfig`", not "I need the config module". The need defines the read, not the file size.

2. **Read the minimum that satisfies the need.**
   Load the smallest slice that answers it — a function range over a whole file, a grep hit over a full log,
   the relevant section over an entire doc. Broad reads spend context you will want later for reasoning.

3. **Distinguish durable facts from transient noise.**
   As you work, separate the few facts worth keeping (the decision made, the interface agreed, the root
   cause found) from the bulk you can discard (intermediate output, explored-and-rejected paths, raw dumps).
   Only durable facts earn a place in persisted memory.

4. **Persist durable state outside the transcript.**
   Write what must survive a resume or handoff into a real artifact — a handoff note, a state file, a
   scratch record — not just the conversation. Context can be compacted or lost; an artifact is recallable.
   Capture: goal, current state, what's done/verified, what's open, the next action.

5. **Drop what no longer pays rent.**
   Actively let go of content whose job is done: closed sub-investigations, superseded plans, verbose output
   you already extracted the answer from. Keeping it "just in case" pollutes the context that steers you.

6. **On resume, re-ground before you trust recall.**
   After a resume or compaction, re-read the handoff artifact and re-probe anything that may have changed,
   rather than acting on a possibly-stale memory of where things stood. Recall is a hypothesis until re-grounded.

7. **Choose re-derive vs recall by cost and staleness.**
   Recall a fact if it is cheap-to-store and stable; re-derive it if it is stale-prone or cheaper to
   recompute than to have carried. A branch name, a file's current contents, a test result after edits —
   re-derive. A design decision or an interface contract — recall from the persisted note.

8. **Keep the working set lean.**
   Periodically ask what is currently loaded that no longer serves the task, and shed it. A tight working
   set of exactly-relevant context outperforms a large one padded with residue.

## Heuristics

- Load the slice, not the file: a function range or grep hit beats reading the whole thing for one fact.
- If you extracted the answer from a dump, drop the dump; keep the answer.
- Anything that must outlive this session goes in an artifact, never only in the transcript.
- A handoff note has five fields: goal, state, done/verified, open, next action — write all five.
- Re-derive stale-prone facts (branch, file contents, test status after edits); recall stable ones (decisions, contracts).
- After compaction or resume, treat every prior fact as unverified until re-grounded from an artifact or probe.
- "Might need it later" is how context fills with noise; load on demand, not on speculation.
- Prefer one lean reference over three overlapping ones; redundant context dilutes the signal that steers you.
- Cost test for recall: if re-deriving is cheaper than the risk of acting on a stale memory, re-derive.
- The transcript is not memory: important state survives only if you deliberately wrote it somewhere durable.
- Summarize before you compact, not after: distill the durable facts into an artifact while the detail is
  still in context, because after compaction the detail you needed to summarize is already gone.
- Load references at the moment of use, not at the start "to have them"; early bulk reads age into noise.

## Anti-patterns

- **Load-everything.** Reading an entire file, log, or module to use one symbol from it, crowding out the
  context you need for reasoning. → Corrective: name the need, load the slice that answers it, stop there.
- **Transcript-as-memory.** Assuming important state is safe because it's "in the conversation", then losing
  it to compaction. → Corrective: persist durable facts into an artifact the moment they're established.
- **Stale recall after resume.** Acting on a remembered branch, value, or file state that changed while you
  were away. → Corrective: re-read the handoff and re-probe changeable facts before the first action.
- **Hoarding.** Keeping closed investigations, rejected paths, and raw output "just in case", polluting the
  working set. → Corrective: drop content once its answer is extracted; a lean context steers better.
- **Redundant re-derivation.** Re-computing an expensive, stable fact every time instead of recording it once.
  → Corrective: persist stable decisions and contracts; re-derive only what actually goes stale.
- **Handoff amnesia.** Ending a session or delegating without writing down goal/state/open/next.
  → Corrective: write the five-field handoff before the boundary, not after someone asks where things stood.

## Relation to existing axes

- **vs exploration-strategy:** exploration is about *acquiring* an accurate model of an unfamiliar codebase —
  what to read to understand it. Context-memory-hygiene is about *managing* what stays loaded, persisted, or
  dropped once acquired — the economics of the window and cross-session memory. Exploration decides what to
  learn; this decides what to keep, write down, and let go.
- **vs incremental-safety:** incremental-safety keeps the *system* green across a sequence of edits.
  Context-memory-hygiene keeps the *agent's working context* clean and its cross-session memory intact.
  One guards the code's state between steps; the other guards the agent's state between turns and sessions.

## Worked example

*Illustrative construction, not a recorded run.*

Task: "Continue the migration from the handoff — three tables done, four to go." Resumed session, context was compacted.

```
Agent does NOT trust its faded memory of "three done" → re-grounds first: re-reads the handoff artifact
    (.omc/handoffs/migration.md) for goal/state/done/open/next.
Handoff says tables A,B,C migrated; D next; interface contract = new `id` is uuid not int (a durable decision).
Agent re-derives the stale-prone facts rather than recalling: `git status` (working tree state) and a probe
    of which tables actually exist migrated in the DB — because those could have changed since the note.
Probe disagrees with the note: table C's migration is half-applied. The note was optimistic. Agent trusts
    the live probe over recall, fixes C first.
For table D, agent needs one thing: the source schema of D. Loads only that table's DDL, not the whole
    schema dump — keeps the window free for the reasoning.
After migrating D and verifying, agent extracts the result, DROPS the verbose migration log, and updates
    the handoff (state: A–D done+verified, E next, uuid-contract still holds).
Exit: durable contract recalled from artifact, stale progress re-derived by probe, working set kept to the
    one table in flight — no context spent on the four not-yet-touched tables.
```

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
