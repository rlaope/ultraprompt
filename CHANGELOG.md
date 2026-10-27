# Changelog

## Unreleased

- `tools/extract_trace.py` follows the Claude Code 2.1.28x–2.1.311 transcript format (trace schema 2). Before, on a current transcript it emitted every peer hand-back and task notification as a plain prompt (one real session: 2,216 prompt events, of which the new classifier marks 236 as human; 1,851 peer, 369 task, 28 command), dropped the `isMeta` peer hand-backs entirely, never read `<session>/subagents/**/agent-*.jsonl` (17 subagents and their tool calls missing from another session), and took the first model seen, which would be `<synthetic>` when a session opens on an API error. Now every prompt carries a `source` (`human`, `peer`, `task`, `command`, `auto`, from `origin.kind` with a text-prefix fallback for older transcripts), compaction summaries become `compaction` events, subagent transcripts are appended after the main events behind a `subagent` header (agent type, spawning tool call; `--no-subagents` skips them), persisted tool outputs are flagged, and stats gain per-model turn counts, prompt sources, compactions and `thinking_omitted`. A bare session id is resolved under `~/.claude/projects/` (`CLAUDE_CONFIG_DIR` respected).
- `extract_trace.py` warns when thinking blocks were stored without text. In the real transcripts checked, 1,372 of 1,398 and 2,165 of 2,343 thinking blocks were signature-only; `_SIMULATION.md` step 2 now says to run case sessions interactively with `showThinkingSummaries: true` and records that `claude -p` on 2.1.311 stored no thinking text either way.
- `tools/check_cases.py` rejects a cited schema-2 trace with no assistant turn from the source model (`trace.SOURCE_MODELS`, `claude-fable-5-1`). Schema-1 traces still verify.
- Target-agent lineup in README and `skills/_TEMPLATE.md` moved to the current public models: Claude Opus 5.5, Sonnet 5.5, Haiku 5.5 (was Opus 5, Sonnet 5, Haiku 4.5, all legacy since the 5.5 family shipped). Fable 5.1 stays the source model; it is still the current Fable per Anthropic's models page.
- Tests: a modern-format fixture (origin kinds, `isMeta` peer hand-back, compaction, persisted output, `<synthetic>` turn, one subagent with a meta file), a non-Fable fixture, session-id lookup, schema-1 compatibility. 14 tests.
- `tools/extract_trace.py`: pipeline step 3 as code. Reads a Claude Code session transcript (`.jsonl`) and writes a normalized trace (prompts, thinking, text, tool calls and results in order, sidechain and error flags, per-tool stats) to the gitignored `based/traces/`, then prints `<session-id>@<digest12>` for the `CASES.md` Session cell. Python 3 stdlib only.
- `tools/check_cases.py`: makes "never invent a row" mechanical. Every non-placeholder `CASES.md` row must cite `<session-id>@<digest12>`; where `based/traces/` exists, the trace must exist and its events must still hash to the cited digest. A placeholder row left next to real rows fails. Called from `scripts/validate-skills.sh`; CI checks citation format only, since traces are not published.
- CI runs the tool unit tests (`python3 -m unittest discover -s tools/tests`).
- `.gitattributes`: `*.sh` marked `linguist-detectable=false` so the repository language reflects the Python tooling, and pinned to LF line endings.

## 0.2.0 — 2026-09-15

- Source model updated to **Claude Fable 5.1** across the protocol, template, all status lines, and trace-evidence logs. Target agents stated explicitly: Claude Opus 5 / Sonnet 5 / Haiku 4.5, GPT-class, and open-weight models.
- Twelve skills documented as the published set: the core eight axes plus four drafts (state-probing, honest-reporting, delegation-parallelism, context-memory-hygiene).
- `CASES.md` added to every core skill so each `skills/<name>/` has the same shape: `SKILL.md` + trace-evidence log.
- `scripts/validate-skills.sh`: enforces the authoring contract (frontmatter name/description, verbatim status line matching `_SIMULATION.md` and the template, section order, 120-220 line budget, no template leftovers, `CASES.md` present, no stale model name, README links in both directions, expected skill count, manifest JSON and version parity). Runs in CI via `.github/workflows/validate.yml`, together with an installer smoke test.
- `install.sh`: `--copy` mode (for environments where symlinked skill directories are not picked up), `--uninstall` driven by an install manifest (`<skills dir>/.ultraprompt-installed`) so it removes exactly what was installed regardless of where the script is run from, `--help`, `CLAUDE_SKILLS_DIR` / `ULTRAPROMPT_DIR` overrides, and a guard that moves a pre-existing real directory aside instead of deleting it.
- `_SIMULATION.md`: provenance rule rewritten from the publishing side (this repo is the mirror; maestro-ultra is the working copy), router wording made harness-neutral.
- README: pipeline and structure updated, install verified against the plugin docs, "use with other agents" section, repository structure reflects what actually ships.
- Plugin manifests: version 0.2.0, `homepage`/`repository`/`license`/`keywords` filled in.

## 0.1.0

- Initial scaffold: README, `skills/_TEMPLATE.md`, eight core strategy skills, four draft axes mirrored from maestro-ultra with `_SIMULATION.md`.
