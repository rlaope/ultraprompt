"""Normalized trace format shared by extract_trace.py and check_cases.py.

A trace is the event sequence of one Claude Code session, reduced to what a CASES.md row
can cite: prompts, thinking, text, tool calls and tool results in transcript order,
followed by each subagent's events. Its digest covers the events only, so a CASES.md row
pinned to `<session>@<digest12>` stops matching the moment the cited events change.

Schema 2 adds, over schema 1: a `source` on every prompt (human, peer, task, command),
compaction boundaries, subagent transcripts, assistant turns per model, and a count of
thinking blocks the transcript stored without their text. Schema 1 traces still verify.
"""
import hashlib
import json

SCHEMA = 2
DIGEST_LEN = 12

# The model case runs are executed on (README, _SIMULATION.md step 2). check_cases.py
# rejects a cited schema-2 trace with no assistant turn from one of these ids. Change it
# together with the status line in _SIMULATION.md, skills/_TEMPLATE.md and
# scripts/validate-skills.sh.
SOURCE_MODELS = ("claude-fable-5-1",)


def digest(events):
    canon = json.dumps(events, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def source_model_turns(t):
    """Assistant turns in trace `t` from a SOURCE_MODELS model, or None for a schema-1 trace."""
    models = (t.get("stats") or {}).get("models")
    if models is None:
        return None
    return sum(n for m, n in models.items() if m in SOURCE_MODELS)
