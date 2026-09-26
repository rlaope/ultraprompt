#!/usr/bin/env python3
"""Extract a normalized trace from a Claude Code session transcript (pipeline step 3).

    python3 tools/extract_trace.py ~/.claude/projects/<project>/<session>.jsonl
    python3 tools/extract_trace.py <session>.jsonl --out-dir based/traces

Writes <out-dir>/<session-id>.json and prints the value to cite in a CASES.md Session
cell: `<session-id>@<digest12>`. The default out-dir is based/traces/, which is
gitignored: traces stay in the local lab, only the citation ships. Stdlib only.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _result_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict) and b.get("type") == "text":
                parts.append(b.get("text", ""))
            elif isinstance(b, dict):
                parts.append("[%s]" % b.get("type", "block"))
        return "\n".join(parts)
    return ""


def extract(lines):
    """Turn transcript lines (already JSON-decoded) into (session_id, model, events)."""
    events = []
    seen = set()
    tool_names = {}
    session_id = model = None

    def add(rec, **ev):
        ev["seq"] = len(events)
        ev["ts"] = rec.get("timestamp")
        if rec.get("isSidechain"):
            ev["sidechain"] = True
        events.append(ev)

    for rec in lines:
        if rec.get("type") not in ("user", "assistant"):
            continue  # summaries, system notes, file-history snapshots
        uid = rec.get("uuid")
        if uid is not None:
            if uid in seen:
                continue
            seen.add(uid)
        session_id = session_id or rec.get("sessionId")
        msg = rec.get("message") or {}
        content = msg.get("content")

        if rec["type"] == "assistant":
            model = model or msg.get("model")
            for b in content if isinstance(content, list) else []:
                t = b.get("type")
                if t == "thinking" and b.get("thinking"):
                    add(rec, kind="thinking", text=b["thinking"])
                elif t == "text" and b.get("text"):
                    add(rec, kind="text", text=b["text"])
                elif t == "tool_use":
                    tool_names[b.get("id")] = b.get("name")
                    add(rec, kind="tool_call", tool=b.get("name"), id=b.get("id"), input=b.get("input"))
            continue

        if rec.get("isMeta"):
            continue  # harness-injected caveats, not the user's words
        if isinstance(content, str):
            add(rec, kind="prompt", text=content)
            continue
        for b in content if isinstance(content, list) else []:
            t = b.get("type")
            if t == "tool_result":
                tid = b.get("tool_use_id")
                ev = {"kind": "tool_result", "id": tid, "tool": tool_names.get(tid),
                      "text": _result_text(b.get("content"))}
                if b.get("is_error"):
                    ev["is_error"] = True
                add(rec, **ev)
            elif t == "text" and b.get("text"):
                add(rec, kind="prompt", text=b["text"])
    return session_id, model, events


def stats(events):
    calls = [e for e in events if e["kind"] == "tool_call"]
    tools = {}
    for e in calls:
        tools[e["tool"]] = tools.get(e["tool"], 0) + 1
    first_edit = next((e["seq"] for e in calls if e["tool"] in EDIT_TOOLS), None)
    return {
        "events": len(events),
        "thinking": sum(e["kind"] == "thinking" for e in events),
        "tool_calls": len(calls),
        "tool_errors": sum(bool(e.get("is_error")) for e in events),
        "tools": dict(sorted(tools.items())),
        "first_edit_seq": first_edit,
    }


def build(path):
    lines = []
    with open(path, encoding="utf-8") as fh:
        for n, raw in enumerate(fh, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                lines.append(json.loads(raw))
            except json.JSONDecodeError:
                print("warn: %s:%d is not JSON, skipped" % (path, n), file=sys.stderr)
    session_id, model, events = extract(lines)
    session_id = session_id or os.path.splitext(os.path.basename(path))[0]
    return {
        "schema": trace.SCHEMA,
        "session_id": session_id,
        "source": os.path.basename(path),
        "model": model,
        "digest": trace.digest(events),
        "stats": stats(events),
        "events": events,
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("transcript", help="Claude Code session .jsonl")
    ap.add_argument("--out-dir", default="based/traces", help="default: based/traces (gitignored)")
    args = ap.parse_args(argv)

    t = build(args.transcript)
    if not t["events"]:
        print("error: no user/assistant events in %s" % args.transcript, file=sys.stderr)
        return 1
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, t["session_id"] + ".json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(t, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    s = t["stats"]
    print("wrote %s (%d events, %d tool calls, %d errors, model %s)"
          % (out, s["events"], s["tool_calls"], s["tool_errors"], t["model"]), file=sys.stderr)
    print("%s@%s" % (t["session_id"], t["digest"][: trace.DIGEST_LEN]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
