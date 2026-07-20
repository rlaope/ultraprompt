# ultraprompt

A project to distill the reasoning traces of a frontier coding model into portable strategy skills for other agents. (v0.1 — see [Status](#status) for what has actually landed.)

The pipeline: run a broad set of coding cases — frontend state machines, high-traffic backends, ML training loops, kernel optimization and quantization, agentic harnesses, low-level Linux — on Claude Fable 5 via Claude Code; extract from the session transcripts how the model actually solves problems: what it explores first, how many hypotheses it keeps alive, what it accepts as evidence of "done", when it abandons an approach; distill those recurring strategies into English skill prompts intended to make Claude Opus (and any other agent that reads a system prompt) reason more like the stronger model. The output is not code. It is a set of carefully written prompts, to be grounded in trace evidence as case runs land.

## How it works

```
 (1) curate            (2) run              (3) extract           (4) distill          (5) publish
 ~16 case domains  →   Fable 5 via      →   full reasoning    →   recurring        →   skills/<axis>/
 frontend, servers,    Claude Code          trace: thinking       strategies along     SKILL.md
 ML, kernels,          sessions             blocks, tool-call     8 orthogonal
 agents, syscalls,                          sequences, self-      axes
 storage, ...                               corrections
```

1. **Curate cases.** A catalog of ~16 domains (frontend, UI design, high-traffic servers, distributed systems, ML training, kernel/quantization, agentic harnesses, CLI/Linux, compilers, storage engines, networking, security, data engineering, testing/legacy, concurrency, games) with per-case difficulty and a note on which reasoning mode each case is designed to provoke. Design-type, debugging-type, and optimization-type cases within the same domain stress different strategies on purpose.
2. **Run on Fable 5.** Each case is executed as a real Claude Code session, not a one-shot completion, so the model plans, calls tools, hits failures, and recovers.
3. **Extract the trace.** From the session transcript we keep the full reasoning surface: thinking blocks, the exact tool-call sequence, dead ends, and self-corrections — not just the final diff.
4. **Distill.** Traces from unrelated domains are compared along 8 orthogonal strategy axes. A behavior counts as a strategy only when it recurs across domains.
5. **Publish.** Each axis becomes one skill: a `SKILL.md` prompt with the strategy stated operationally, plus trace-evidence sections that cite the runs it was observed in.

## The 8 strategy axes

| Skill | What it encodes |
|---|---|
| [exploration-strategy](skills/exploration-strategy/SKILL.md) | The order in which to build a mental model of an unfamiliar codebase or problem before touching anything. |
| [hypothesis-management](skills/hypothesis-management/SKILL.md) | How many competing explanations to keep alive, how to rank them, and what evidence retires one. |
| [verification-discipline](skills/verification-discipline/SKILL.md) | What counts as proof that something works — tests, benchmarks, reproductions — and what never does. |
| [tradeoff-articulation](skills/tradeoff-articulation/SKILL.md) | Quantifying alternatives and stating the decision and its cost out loud instead of picking silently. |
| [failure-mode-enumeration](skills/failure-mode-enumeration/SKILL.md) | Systematically listing edge cases and failure scenarios before implementation, not after the bug report. |
| [self-correction-loop](skills/self-correction-loop/SKILL.md) | The triggers for abandoning an approach and how to change course without thrashing. |
| [spec-to-code-fidelity](skills/spec-to-code-fidelity/SKILL.md) | Cross-checking habits when translating an RFC, paper, or formula into code. |
| [incremental-safety](skills/incremental-safety/SKILL.md) | Splitting a large change into intermediate states that are each safe to stop at. |

Skills are organized by **strategy, not domain**. A collaborative kanban board and an LSM-tree key-value store look nothing alike, but both force the model to quantify a trade-off (optimistic-update conflict cost vs. write/read amplification) — and the bet is that traces will show the same articulation pattern in both. Domain-sliced skills would duplicate that pattern sixteen times and generalize zero times; axis-sliced skills capture it once and transfer it anywhere.

The axes are deliberately orthogonal: each names a distinct decision the model makes during a session, and any single case run gets scored on all eight. A debugging case might contribute strong evidence to `hypothesis-management` and `self-correction-loop` while saying nothing about `tradeoff-articulation`; a greenfield design case contributes the reverse. Coverage of each axis therefore accumulates from many cases, not from one designated "exploration case".

### What a SKILL.md contains

Every skill follows the same template (`skills/_TEMPLATE.md`):

- **Frontmatter description** — the one-line trigger written for a router: an orchestrator reads only this line to decide whether to load the skill.
- **When to apply** — trigger conditions an agent can check against its current task state ("the failing behavior cannot yet be reproduced on demand"), not vibes.
- **Core loop** — numbered imperative steps addressed to a coding agent, with at least one explicit exit condition.
- **Heuristics** — threshold-based decision rules ("after 2 failed attempts", "keep at most 3 live hypotheses") that resolve real forks the agent hits mid-loop.
- **Anti-patterns** — the failure behaviors a capable-but-unguided agent actually exhibits, each paired with a corrective move.
- **Worked example** — one compact scenario applying the loop end-to-end; an illustrative construction until a real trace replaces it.
- **Trace evidence** — citations of the case runs where the pattern was observed, with what the model did at that point. (Empty in v0.1; see Status.)

## Install

These are prompts, not code — there is nothing to build or execute. Install them one of three ways.

**Claude Code plugin** — adds the marketplace and installs every skill:

<!-- needs-verification: plugin/marketplace command form and manifest schema (.claude-plugin/marketplace.json, plugin.json) unverified on a clean machine; confirm `ultraprompt@ultraprompt` resolves once the repo is public. -->

```
/plugin marketplace add rlaope/ultraprompt
/plugin install ultraprompt@ultraprompt
```

**One-line install** — clones the repo and symlinks every skill into `~/.claude/skills/`:

```sh
curl -fsSL https://raw.githubusercontent.com/rlaope/ultraprompt/main/install.sh | sh
```

**No terminal?** Just tell your coding agent:

```text
hey, install this: https://github.com/rlaope/ultraprompt
```

Load the axes you need, not all eight — each skill is independent, and stacking all of them inflates context for little gain on a task that stresses only one or two. For agents other than Claude Code, paste the body of a `SKILL.md` into the system prompt (or the `system` parameter of an API call); the skills are self-contained English with no Claude Code-specific syntax in their operative sections.

## Status

**v0.1 — baseline drafts.** All eight skills exist as structured drafts derived from the case catalog and the axis definitions. No case runs have been executed yet; the trace-evidence sections in each `SKILL.md` are placeholders and will be filled in as runs land, one batch at a time (first batch: 8 cases, one per axis-representative domain). Until then, treat the skills as informed hypotheses about frontier-model strategy, not measured findings. Wording will change as evidence accumulates; axis boundaries are expected to hold.

## Repository structure

```
ultraprompt/
├── README.md                      # this file — the front page of the published repo
├── skills/                        # PUBLISHED: the 8 strategy skills, English
│   ├── _TEMPLATE.md               # authoring template every SKILL.md follows
│   ├── exploration-strategy/
│   │   └── SKILL.md
│   ├── hypothesis-management/
│   │   └── SKILL.md
│   ├── verification-discipline/
│   │   └── SKILL.md
│   ├── tradeoff-articulation/
│   │   └── SKILL.md
│   ├── failure-mode-enumeration/
│   │   └── SKILL.md
│   ├── self-correction-loop/
│   │   └── SKILL.md
│   ├── spec-to-code-fidelity/
│   │   └── SKILL.md
│   └── incremental-safety/
│       └── SKILL.md
├── based/                         # LOCAL LAB, gitignored — never ships
│   ├── CASES.md                   # case catalog: ~16 domains, difficulty, axis mapping
│   ├── TRACING.md                 # guide for extracting traces from session transcripts
│   ├── templates/
│   │   └── trace-note.md          # per-run trace note template (8-axis observation grid)
│   └── cases/<id>/                # future: one dir per case run — prompt, artifacts, trace notes
└── .gitignore                     # excludes based/ and operational state
```

`based/` is the working lab: case code, raw traces, and notes live there and stay local. The published surface of this repository is exactly `README.md` and `skills/` — nothing else ships.
