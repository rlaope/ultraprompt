---
name: <kebab-case-name>
description: <one line — when an agent should invoke this skill>
---
<!-- name: must match the skill's directory name (skills/<name>/SKILL.md). One skill = one strategy axis. -->
<!-- description: written for a router — an orchestrator reads only this line to decide whether to load the skill. -->

# <Human Title>
<!-- Title the STRATEGY, not the domain. "Hypothesis Management", not "Debugging Python". -->

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.
<!-- Keep this line verbatim until at least one trace-evidence row is real; then bump version and reword to reflect the evidence. -->

## When to apply
<!-- 3-6 trigger conditions as bullets. Conditions an agent can check against its current task state, not vibes. Good: "The failing behavior cannot yet be reproduced on demand." Bad: "When debugging is hard." -->
- <trigger condition 1>
- <trigger condition 2>
- <trigger condition 3>

## Core loop
<!-- The heart of the file. 5-10 numbered steps, imperative voice, addressed TO a coding agent ("Run X", "Do not edit until Y"). Each step must be executable — an agent should know exactly what tool call or decision it implies. Include at least one explicit exit/stop condition. -->
1. <first step — usually an observation or scoping action>
2. <step>
3. <step>
4. <step>
5. <step — include the loop-back or exit condition, e.g. "If X fails, return to step 2 with the failure as new evidence; otherwise stop.">

## Heuristics
<!-- At least 6 concrete decision rules, one line each. Prefer numbers and thresholds over adjectives: "after 2 failed attempts", "if the diff exceeds ~50 lines", "keep at most 3 live hypotheses". Each line should resolve a real fork the agent hits mid-loop. -->
- <rule with a threshold or a decisive test>
- <rule>
- <rule>
- <rule>
- <rule>
- <rule>

## Anti-patterns
<!-- 4-6 failure patterns. Format each as: the failure behavior → the corrective move. These are the mistakes a capable-but-unguided agent actually makes, not strawmen. -->
- **<failure pattern name>**: <what it looks like>. → <corrective move>.
- **<failure pattern name>**: <what it looks like>. → <corrective move>.
- **<failure pattern name>**: <what it looks like>. → <corrective move>.
- **<failure pattern name>**: <what it looks like>. → <corrective move>.

## Worked example
<!-- One compact concrete scenario, ~15-30 lines, showing the loop applied end-to-end. Pseudo-trace style is the target register: "Agent observes X → does Y because Z". Pick a scenario from a DIFFERENT domain than the ones the reader will assume, to prove the strategy generalizes. Never fabricate a real case-run result here — this is an illustrative construction until traces exist. Keep the preface line below until a real trace replaces the construction. -->

*Illustrative construction, not a recorded run.*

<scenario setup: 1-2 lines of task + starting state>

```
Agent observes <initial evidence> → <action> because <heuristic applied>.
<result of action> → agent updates <state/hypothesis> to <new value>.
...
Exit: <which stop condition fired and what evidence closed the loop>.
```

## Trace evidence
<!-- Populated only from real case runs recorded in based/. One row per session that exercised this strategy. Never invent rows. The "What it showed" column should name which section above the trace confirmed, contradicted, or refined. -->

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |

<!--
AUTHORING RULES (delete this block in real skill files):
- English only. Direct, dense, zero marketing fluff.
- 120-220 lines per finished skill file.
- The quality test: pasting this file into an Opus system prompt should measurably
  change how it works on a matching task. If a section wouldn't change behavior, cut it.
- Skills map 1:1 to the 8 strategy axes in based/CASES.md:
  exploration-strategy, hypothesis-management, verification-discipline,
  tradeoff-articulation, failure-mode-enumeration, self-correction-loop,
  spec-to-code-fidelity, incremental-safety.
- Optional strategy-specific sections (a checklist, a selection guide) may be
  inserted between the core sections when the strategy needs them; the core
  sections above and their order stay fixed.
- No AI attribution anywhere.
-->
