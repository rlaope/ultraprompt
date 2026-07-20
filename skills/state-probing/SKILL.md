---
name: state-probing
description: Invoke before acting on any assumption about the runtime or environment — versions, running processes, file/disk reality, git state, network reachability. Grounds claims about the world in a cheap probe instead of a guess, and re-probes when state may have gone stale.
---
# State Probing

> Status: v0.1 baseline draft — derived from the case catalog and axis definitions; awaiting trace evidence from Fable 5 case runs.

## When to apply

- You are about to run a command, edit a file, or report a result whose correctness depends on the state of
  the environment (which version is installed, whether a process is up, what branch you are on).
- A step failed in a way that only makes sense if reality differs from your assumption ("but I installed it").
- You resumed a session, a build ran, or time passed — any earlier probe result may now be stale.
- You are inferring environment state from source, config, or memory instead of from the live system.
- You are about to claim something *is* true of the world ("the server is running", "the file exists",
  "we're on main") rather than something you *did*.
- The plan's next action is destructive or expensive and assumes a precondition you have not confirmed.

## Core loop

1. **Name the assumption as a checkable proposition.**
   Turn the vague belief into one testable claim about the world: "node is v20", "port 5173 is listening",
   "the working tree is clean", "`.env` contains `API_KEY`". If you cannot phrase it as something a single
   command could confirm or deny, it is not yet a probe target — sharpen it first.

2. **Pick the cheapest probe that discriminates.**
   Choose the command whose output *distinguishes* the assumption from its negation with the least cost and
   least side effect. `node --version` beats reading a lockfile; `git status --short` beats `git log`;
   `curl -sI localhost:PORT` beats starting a client. A probe that cannot come back false is not a probe.

3. **Run the probe and read the actual output.**
   Execute it. Read the real bytes — exit code, version string, PID, branch name — not what you expected
   them to say. The point of probing is to be surprised; skimming for the expected answer defeats it.

4. **Distinguish "absent" from "unknown".**
   A probe that errored, timed out, or returned nothing is not evidence of absence. `pgrep` returning
   nothing means the process is not running *or* the name is wrong. Confirm the probe itself worked before
   trusting its silence.

5. **Act only inside what the probe established.**
   Take the next step only within the state you just confirmed. If the action's precondition was not the
   thing you probed, you have not earned the action — go back to step 1 for the real precondition.

6. **Re-probe on any staleness signal.**
   After a build, install, checkout, resume, long gap, or another agent's turn, treat prior probe results
   as expired. Re-run the probe rather than reusing a remembered value. State you confirmed 40 tool-calls
   ago is a memory, not a measurement.

7. **Report the ground truth you observed, not the assumption you started with.**
   State what the probe showed ("git status: 3 modified, on `feature/x`"), and if you could not probe,
   say the claim is unverified — never launder an assumption into a fact.

## Heuristics

- Probe before every irreversible or expensive action whose precondition you have not confirmed this turn.
- The cheapest discriminating probe wins: prefer a one-line status query over spinning up the real client.
- One probe answers one proposition. If your command's output can't be false, it isn't testing anything.
- Version/tool claims cost one command (`--version`, `which`) — never assert a version from memory or a manifest.
- Treat "it worked a minute ago" as expired after any state-changing event; re-probe rather than recall.
- Empty output is ambiguous: confirm the probe ran (exit 0, correct target) before reading silence as "none".
- Prefer the runtime source of truth over its declaration: a running process over a config file, `git status`
  over what you think you committed, `ls` over the path you expect exists.
- If two probes disagree (lockfile says X, `--version` says Y), the live runtime wins and X is the bug.
- Budget the probing: 2–4 targeted probes to ground a task is discipline; probing every trivial fact is noise.
- When you cannot probe (no access, sandbox), downgrade every dependent claim to "assumed", not "confirmed".
- A probe that changes state is not a probe: prefer read-only queries; if the only check has side effects, note them.
- Ground the surprising result, not the expected one: when a probe confirms your belief, move on; when it
  contradicts it, that contradiction is the highest-value fact in the session — act on it first.

## Anti-patterns

- **Assumed-state action.** Running the fix on the belief the service is up / the branch is right / the
  dep is installed, without a single confirming command. → Corrective: name the precondition and probe it
  before the action, not after it fails.
- **Stale recall.** Reusing a version, PID, or branch you checked long ago and several state-changes back.
  → Corrective: re-probe after any build/install/checkout/resume; a remembered value is not a measurement.
- **Reading the declaration for the reality.** Trusting `package.json`, a Dockerfile, or docs for what is
  *actually* installed and running. → Corrective: query the live runtime; let the declaration be the hypothesis.
- **Silence as absence.** Concluding "not running" / "not there" from an empty or errored probe without
  confirming the probe itself was valid. → Corrective: verify the probe targeted the right thing and exited
  cleanly before trusting its emptiness.
- **Over-probing.** Burning turns confirming facts that don't gate any action, or re-probing unchanged state
  every step. → Corrective: probe only what a decision depends on, and only after a staleness signal.

## Relation to existing axes

- **vs exploration-strategy:** exploration builds a mental model of the **code** — what functions exist,
  how a request flows through the modules. State-probing grounds claims about the **runtime/environment** —
  what is installed, running, checked out, present on disk *right now*. Exploration reads files to understand;
  state-probing runs commands to confirm reality before acting on it.
- **vs verification-discipline:** verification comes *after* a change, to prove the result meets the claim.
  State-probing comes *before* an action, to confirm the preconditions the action assumes. One checks the
  output; the other checks the ground you are standing on.

## Worked example

*Illustrative construction, not a recorded run.*

Task: "The deploy script keeps failing at the migration step — fix it." Autonomous session, resumed from a handoff.

```
Agent restates preconditions as propositions: (a) DB is reachable, (b) migration tool version matches
    the migration files, (c) we're on the branch the handoff described.
Agent picks cheapest discriminating probes: `git rev-parse --abbrev-ref HEAD`, `migrate --version`,
    `pg_isready -h $DB_HOST`.
Probe 1 → branch is `main`, but the handoff said work was on `release/2.3` → assumption (c) FALSE.
Agent stops: acting on main would migrate the wrong tree. Checks out `release/2.3`, then RE-PROBES version
    because the checkout is a staleness signal.
Probe 2 (post-checkout) → `migrate v4`, but migration files use v5 syntax → real cause found without ever
    editing the deploy script.
Agent confirms the probe wasn't lying: `which migrate` → an old global shim shadowing the project binary.
Exit: reports "root cause was environment, not the script — global `migrate` v4 shadowed project v5 on the
    wrong branch. Verified via `migrate --version` after checkout." No code changed on a false assumption.
```

## Trace evidence

| Case | Session | What it showed |
|------|---------|----------------|
| _awaiting case runs_ | — | — |
