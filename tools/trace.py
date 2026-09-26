"""Normalized trace format shared by extract_trace.py and check_cases.py.

A trace is the event sequence of one Claude Code session, reduced to what a CASES.md row
can cite: prompts, thinking, text, tool calls and tool results, in transcript order.
Its digest covers the events only, so a CASES.md row pinned to `<session>@<digest12>`
stops matching the moment the cited events change.
"""
import hashlib
import json

SCHEMA = 1
DIGEST_LEN = 12


def digest(events):
    canon = json.dumps(events, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)
