# Changelog

## Unreleased

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
