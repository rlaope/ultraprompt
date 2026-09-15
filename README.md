# ultraprompt

Portable strategy skills for coding agents, to be distilled from the reasoning traces of a frontier coding model. (v0.2: baseline drafts, trace evidence pending — see [Status](#status) for what has actually landed.)

The pipeline: run a broad set of coding cases — frontend state machines, high-traffic backends, ML training loops, kernel optimization and quantization, agentic harnesses, low-level Linux — on **Claude Fable 5.1** via Claude Code; extract from the session transcripts how the model actually solves problems: what it explores first, how many hypotheses it keeps alive, what it accepts as evidence of "done", when it abandons an approach; distill those recurring strategies into English skill prompts that make a weaker agent — Claude Opus 5, Sonnet 5, Haiku 4.5, a GPT-class model, an open-weight model, anything that reads a system prompt — reason more like the stronger one. The output is not code. It is a set of carefully written prompts, to be grounded in trace evidence as case runs land.

## How it works

```
 (1) curate            (2) run              (3) extract           (4) distill          (5) publish
 ~16 case domains  →   Fable 5.1 via    →   full reasoning    →   recurring        →   skills/<axis>/
 frontend, servers,    Claude Code          trace: thinking       strategies along     SKILL.md
 ML, kernels,          sessions             blocks, tool-call     orthogonal axes      CASES.md
 agents, syscalls,                          sequences, self-      (8 core + 4 draft)
 storage, ...                               corrections
```

1. **Curate cases.** A catalog of ~16 domains (frontend, UI design, high-traffic servers, distributed systems, ML training, kernel/quantization, agentic harnesses, CLI/Linux, compilers, storage engines, networking, security, data engineering, testing/legacy, concurrency, games) with per-case difficulty and a note on which reasoning mode each case is designed to provoke. Design-type, debugging-type, and optimization-type cases within the same domain stress different strategies on purpose.
2. **Run on Fable 5.1.** Each case is executed as a real Claude Code session, not a one-shot completion, so the model plans, calls tools, hits failures, and recovers.
3. **Extract the trace.** From the session transcript we keep the full reasoning surface: thinking blocks, the exact tool-call sequence, dead ends, and self-corrections — not just the final diff.
4. **Distill.** Traces from unrelated domains are compared along orthogonal strategy axes. A behavior counts as a strategy only when it recurs across domains.
5. **Publish.** Each axis becomes one skill: a `SKILL.md` prompt with the strategy stated operationally, plus a `CASES.md` trace-evidence log that cites the runs it was observed in.

## The strategy axes

### Core eight

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

The axes are deliberately orthogonal: each names a distinct decision the model makes during a session, and any single case run gets scored on all of them. A debugging case might contribute strong evidence to `hypothesis-management` and `self-correction-loop` while saying nothing about `tradeoff-articulation`; a greenfield design case contributes the reverse. Coverage of each axis therefore accumulates from many cases, not from one designated "exploration case".

### Draft axes (awaiting trace evidence)

Four candidate axes distilled via the [`_SIMULATION.md`](_SIMULATION.md) protocol (run a real Fable 5.1 session on a representative task, capture the trace, distill the strategy). They are honest drafts: each stays `v0.1 baseline draft` until at least one real trace-evidence row lands in its `CASES.md`, and a candidate that cannot show evidence distinct from the core eight gets absorbed, not shipped.

| Skill | What it encodes |
|---|---|
| [state-probing](skills/state-probing/SKILL.md) | Probing the actual runtime/environment state — versions, processes, git truth — before acting on assumptions. |
| [honest-reporting](skills/honest-reporting/SKILL.md) | Calibrating claims to evidence: verified vs should-work, marking the unmeasured as open, reporting failures plainly. |
| [delegation-parallelism](skills/delegation-parallelism/SKILL.md) | When to split work across agents or sessions vs doing it inline — independence tests, disjoint scopes, coordination cost. |
| [context-memory-hygiene](skills/context-memory-hygiene/SKILL.md) | What to load, persist, and drop across turns and sessions; handoffs without context pollution. |

These are co-developed in [maestro-ultra](https://github.com/animepics/maestro-ultra) (the authoring working copy, where the conductor exercises them) and published here, the upstream home. `_SIMULATION.md` states the promotion bar and the provenance rule.

### What a skill directory contains

Every `skills/<name>/` has the same two files:

- **`SKILL.md`** — the prompt, following `skills/_TEMPLATE.md`:
  - **Frontmatter description** — the one-line trigger written for a router: an orchestrator reads only this line to decide whether to load the skill.
  - **When to apply** — trigger conditions an agent can check against its current task state ("the failing behavior cannot yet be reproduced on demand"), not vibes.
  - **Core loop** — numbered imperative steps addressed to a coding agent, with at least one explicit exit condition.
  - **Heuristics** — threshold-based decision rules ("after 2 failed attempts", "keep at most 3 live hypotheses") that resolve real forks the agent hits mid-loop.
  - **Anti-patterns** — the failure behaviors a capable-but-unguided agent actually exhibits, each paired with a corrective move.
  - **Worked example** — one compact scenario applying the loop end-to-end; an illustrative construction until a real trace replaces it.
  - **Trace evidence** — citations of the case runs where the pattern was observed. (Empty in v0.2; see Status.)
- **`CASES.md`** — the trace-evidence log: one row per real session that exercised the axis (case, session, task/domain, distinctness vs the other axes, and what it confirmed, contradicted, or refined). Rows are recorded from real traces only.

## Install

These are prompts, not code — there is nothing to build or execute. Install them one of three ways.

**Claude Code plugin** — adds the marketplace and installs every skill (manifests in `.claude-plugin/` follow the [plugin](https://code.claude.com/docs/en/plugins) and [marketplace](https://code.claude.com/docs/en/plugin-marketplaces) schema; skills are auto-discovered from `skills/<name>/SKILL.md`):

```
/plugin marketplace add rlaope/ultraprompt
/plugin install ultraprompt@ultraprompt
```

**One-line install** — clones the repo to `~/.ultraprompt` and symlinks every skill into `~/.claude/skills/`:

```sh
curl -fsSL https://raw.githubusercontent.com/rlaope/ultraprompt/main/install.sh | sh
```

Options: `sh -s -- --copy` copies the directories instead of symlinking (for environments that do not follow symlinks), `sh -s -- --uninstall` removes exactly the set recorded in `~/.claude/skills/.ultraprompt-installed` and nothing else, `sh -s -- --help` lists the rest. `CLAUDE_SKILLS_DIR` overrides the destination; `ULTRAPROMPT_DIR` overrides the clone location. The installer never deletes a directory it did not create: a pre-existing one with a skill's name is moved aside as `<name>.bak-<timestamp>` and left there, also by `--uninstall`.

**No terminal?** Just tell your coding agent:

```text
hey, install this: https://github.com/rlaope/ultraprompt
```

Load the axes you need, not all twelve — each skill is independent, and stacking all of them inflates context for little gain on a task that stresses only one or two.

### Use with agents other than Claude Code

The skills are self-contained English with no Claude Code-specific syntax in their operative sections. For any other agent, paste the body of a `SKILL.md` (everything below the frontmatter) into the system prompt, the `system` parameter of an API call, or the project instructions file the agent reads (`AGENTS.md`, `.cursor/rules`, and the like). A useful minimal stack for a general coding agent is `exploration-strategy` + `verification-discipline` + `honest-reporting`; add `hypothesis-management` and `self-correction-loop` for debugging-heavy work.

## Status

**v0.2 — baseline drafts, twelve skills, validated shape.** The core eight skills and the four draft axes exist as structured drafts derived from the case catalog and the axis definitions, and every skill directory now ships a `CASES.md` alongside its `SKILL.md`. No case runs have been executed yet; the trace-evidence sections are placeholders and will be filled in as runs land, one batch at a time (first batch: 8 cases, one per axis-representative domain, on Fable 5.1). Until then, treat the skills as informed hypotheses about frontier-model strategy, not measured findings. Wording will change as evidence accumulates; axis boundaries are expected to hold. Promotion follows `_SIMULATION.md`: no trace row, no promotion.

## Contributing

- Author or change a skill against `skills/_TEMPLATE.md`; new axes go through `_SIMULATION.md` first.
- Run `sh scripts/validate-skills.sh` before opening a pull request. It checks frontmatter, the verbatim status line, section order, the 120-220 line budget, template leftovers, README links, and manifest version parity. CI runs the same script plus an installer smoke test on every push and pull request.
- Never invent a trace-evidence row. `CASES.md` rows come from real sessions only.

## Repository structure

```
ultraprompt/
├── README.md                      # this file — the front page of the published repo
├── CHANGELOG.md
├── _SIMULATION.md                 # how a new axis becomes a skill: protocol, quality bar, provenance
├── install.sh                     # one-line installer: link/copy skills into ~/.claude/skills, --uninstall
├── scripts/
│   └── validate-skills.sh         # authoring-contract checks (run locally and in CI)
├── .github/workflows/validate.yml # CI: validate-skills + installer smoke test
├── .claude-plugin/
│   ├── plugin.json                # Claude Code plugin manifest
│   └── marketplace.json           # single-plugin marketplace pointing at this repo root
├── skills/                        # PUBLISHED: 12 strategy skills, English
│   ├── _TEMPLATE.md               # authoring template every SKILL.md follows
│   ├── exploration-strategy/      # ── core eight ──
│   │   ├── SKILL.md
│   │   └── CASES.md
│   ├── hypothesis-management/
│   ├── verification-discipline/
│   ├── tradeoff-articulation/
│   ├── failure-mode-enumeration/
│   ├── self-correction-loop/
│   ├── spec-to-code-fidelity/
│   ├── incremental-safety/
│   ├── state-probing/             # ── drafts (per _SIMULATION.md) ──
│   ├── honest-reporting/
│   ├── delegation-parallelism/
│   └── context-memory-hygiene/
├── based/                         # LOCAL LAB, gitignored — never ships
│   ├── CASES.md                   # case catalog: ~16 domains, difficulty, axis mapping
│   ├── TRACING.md                 # guide for extracting traces from session transcripts
│   ├── templates/trace-note.md    # per-run trace note template (per-axis observation grid)
│   └── cases/<id>/                # future: one dir per case run — prompt, artifacts, trace notes
└── .gitignore                     # excludes based/ and operational state
```

`based/` is the working lab: case code, raw traces, and notes live there and stay local. The published surface of this repository is `skills/`, the two protocol documents, the installer, and the plugin manifests — nothing else ships.
