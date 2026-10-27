#!/usr/bin/env python3
"""Extract a normalized trace from a Claude Code session transcript (pipeline step 3).

    python3 tools/extract_trace.py ~/.claude/projects/<project>/<session>.jsonl
    python3 tools/extract_trace.py <session-id>              # looked up under ~/.claude/projects/
    python3 tools/extract_trace.py <session>.jsonl --out-dir based/traces --no-subagents

Writes <out-dir>/<session-id>.json and prints the value to cite in a CASES.md Session
cell: `<session-id>@<digest12>`. The default out-dir is based/traces/, which is
gitignored: traces stay in the local lab, only the citation ships. Stdlib only.

Subagent transcripts (`<session>/subagents/**/agent-*.jsonl`, written by Claude Code
2.1.28x and later) are appended after the main events, each opened by a `subagent` event
that names the agent type and the tool call that spawned it.
"""
import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace  # noqa: E402

EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}

# Who wrote a prompt. Claude Code 2.1.29x+ records it in `origin.kind`; older transcripts
# only carry the text, so the prefixes below are the fallback.
ORIGIN_SOURCES = {
    "human": "human",
    "peer": "peer",
    "task-notification": "task",
    "auto-continuation": "auto",
}
PREFIX_SOURCES = (
    ("Another Claude session sent a message", "peer"),
    ("<task-notification>", "task"),
    ("<command-name>", "command"),
    ("<local-command-stdout>", "command"),
    ("<local-command-caveat>", "command"),
    ("<bash-input>", "command"),
    ("<bash-stdout>", "command"),
)
# isMeta prompts are harness-injected (skill bodies, caveats, image stubs) and are dropped,
# except for these sources: a peer hand-back or task notification is input the model acts on.
META_KEPT = {"peer", "task"}


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


def prompt_source(rec, text):
    origin = rec.get("origin")
    kind = origin.get("kind") if isinstance(origin, dict) else None
    if kind in ORIGIN_SOURCES:
        return ORIGIN_SOURCES[kind]
    for prefix, source in PREFIX_SOURCES:
        if text.startswith(prefix):
            return source
    return "human"


def extract(lines, agent=None, start=0):
    """Turn transcript lines (already JSON-decoded) into (session_id, info, events).

    `agent` tags every event with a subagent id; `start` offsets `seq` so a subagent's
    events continue the main sequence.
    """
    events = []
    seen = set()
    tool_names = {}
    session_id = None
    info = {"models": {}, "thinking_omitted": 0}

    def add(rec, **ev):
        ev["seq"] = start + len(events)
        ev["ts"] = rec.get("timestamp")
        if agent:
            ev["agent"] = agent
        elif rec.get("isSidechain"):
            ev["sidechain"] = True
        events.append(ev)

    for rec in lines:
        if rec.get("type") not in ("user", "assistant"):
            continue  # summaries, system notes, attachments, file-history snapshots
        uid = rec.get("uuid")
        if uid is not None:
            if uid in seen:
                continue
            seen.add(uid)
        session_id = session_id or rec.get("sessionId")
        msg = rec.get("message") or {}
        content = msg.get("content")

        if rec["type"] == "assistant":
            m = msg.get("model")
            if m:
                info["models"][m] = info["models"].get(m, 0) + 1
            for b in content if isinstance(content, list) else []:
                t = b.get("type")
                if t == "thinking":
                    if b.get("thinking"):
                        add(rec, kind="thinking", text=b["thinking"])
                    else:
                        info["thinking_omitted"] += 1  # signature only: the text was not stored
                elif t == "redacted_thinking":
                    info["thinking_omitted"] += 1
                elif t == "text" and b.get("text"):
                    add(rec, kind="text", text=b["text"])
                elif t == "tool_use":
                    tool_names[b.get("id")] = b.get("name")
                    add(rec, kind="tool_call", tool=b.get("name"), id=b.get("id"), input=b.get("input"))
            continue

        if rec.get("isCompactSummary"):
            text = content if isinstance(content, str) else _result_text(content)
            add(rec, kind="compaction", text=text)
            continue
        if isinstance(content, str):
            source = prompt_source(rec, content)
            if not rec.get("isMeta") or source in META_KEPT:
                add(rec, kind="prompt", source=source, text=content)
            continue
        for b in content if isinstance(content, list) else []:
            t = b.get("type")
            if t == "tool_result":
                tid = b.get("tool_use_id")
                text = _result_text(b.get("content"))
                ev = {"kind": "tool_result", "id": tid, "tool": tool_names.get(tid), "text": text}
                if b.get("is_error"):
                    ev["is_error"] = True
                if text.startswith("<persisted-output>"):
                    ev["persisted"] = True  # full output lives in <session>/tool-results/
                add(rec, **ev)
            elif t == "text" and b.get("text"):
                source = prompt_source(rec, b["text"])
                if not rec.get("isMeta") or source in META_KEPT:
                    add(rec, kind="prompt", source=source, text=b["text"])
    return session_id, info, events


def read_jsonl(path):
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
    return lines


def subagent_files(path):
    """Subagent transcripts that belong to the session at `path`, oldest first."""
    root = os.path.join(os.path.splitext(path)[0], "subagents")
    files = glob.glob(os.path.join(root, "**", "agent-*.jsonl"), recursive=True)
    return sorted(files, key=lambda f: (os.path.getmtime(f), f))


def stats(events, info, subagents):
    calls = [e for e in events if e["kind"] == "tool_call"]
    tools = {}
    for e in calls:
        tools[e["tool"]] = tools.get(e["tool"], 0) + 1
    sources = {}
    for e in events:
        if e["kind"] == "prompt":
            sources[e["source"]] = sources.get(e["source"], 0) + 1
    main_calls = [e for e in calls if "agent" not in e]
    first_edit = next((e["seq"] for e in main_calls if e["tool"] in EDIT_TOOLS), None)
    return {
        "events": len(events),
        "prompts": dict(sorted(sources.items())),
        "thinking": sum(e["kind"] == "thinking" for e in events),
        "thinking_omitted": info["thinking_omitted"],
        "compactions": sum(e["kind"] == "compaction" for e in events),
        "tool_calls": len(calls),
        "tool_errors": sum(bool(e.get("is_error")) for e in events),
        "persisted_outputs": sum(bool(e.get("persisted")) for e in events),
        "tools": dict(sorted(tools.items())),
        "first_edit_seq": first_edit,
        "models": dict(sorted(info["models"].items())),
        "subagents": subagents,
    }


def _merge(info, more):
    for m, n in more["models"].items():
        info["models"][m] = info["models"].get(m, 0) + n
    info["thinking_omitted"] += more["thinking_omitted"]


def build(path, subagents=True):
    session_id, info, events = extract(read_jsonl(path))
    session_id = session_id or os.path.splitext(os.path.basename(path))[0]
    n_sub = 0
    if subagents:
        for f in subagent_files(path):
            agent = os.path.basename(f)[len("agent-"):-len(".jsonl")]
            meta_path = f[: -len(".jsonl")] + ".meta.json"
            meta = trace.load(meta_path) if os.path.isfile(meta_path) else {}
            _, sub_info, sub_events = extract(read_jsonl(f), agent=agent, start=len(events) + 1)
            if not sub_events:
                continue
            head = {"kind": "subagent", "agent": agent, "seq": len(events),
                    "ts": sub_events[0]["ts"], "agent_type": meta.get("agentType"),
                    "description": meta.get("description"), "spawned_by": meta.get("toolUseId")}
            events.append(head)
            events.extend(sub_events)
            _merge(info, sub_info)
            n_sub += 1
    model = max((m for m in info["models"] if m != "<synthetic>"),
                key=lambda m: info["models"][m], default=None)
    return {
        "schema": trace.SCHEMA,
        "session_id": session_id,
        "source": os.path.basename(path),
        "model": model,
        "digest": trace.digest(events),
        "stats": stats(events, info, n_sub),
        "events": events,
    }


def resolve(arg):
    """A transcript path, or a bare session id looked up under the Claude Code projects dir."""
    if os.path.isfile(arg) or arg.endswith(".jsonl"):
        return arg
    base = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    hits = glob.glob(os.path.join(base, "projects", "*", arg + ".jsonl"))
    if len(hits) == 1:
        return hits[0]
    print("error: %s matches %d transcripts under %s/projects" % (arg, len(hits), base), file=sys.stderr)
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("transcript", help="Claude Code session .jsonl, or a session id")
    ap.add_argument("--out-dir", default="based/traces", help="default: based/traces (gitignored)")
    ap.add_argument("--no-subagents", action="store_true", help="skip <session>/subagents/ transcripts")
    args = ap.parse_args(argv)

    path = resolve(args.transcript)
    if path is None:
        return 1
    t = build(path, subagents=not args.no_subagents)
    if not t["events"]:
        print("error: no user/assistant events in %s" % path, file=sys.stderr)
        return 1
    os.makedirs(args.out_dir, exist_ok=True)
    out = os.path.join(args.out_dir, t["session_id"] + ".json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(t, fh, ensure_ascii=False, indent=1)
        fh.write("\n")
    s = t["stats"]
    print("wrote %s (%d events, %d tool calls, %d errors, %d subagents, model %s)"
          % (out, s["events"], s["tool_calls"], s["tool_errors"], s["subagents"], t["model"]), file=sys.stderr)
    if s["thinking_omitted"]:
        print("warn: %d of %d thinking block(s) were stored without text; the trace lacks that reasoning"
              " (see _SIMULATION.md step 2 on showThinkingSummaries)"
              % (s["thinking_omitted"], s["thinking_omitted"] + s["thinking"]), file=sys.stderr)
    if not trace.source_model_turns(t):
        print("warn: no assistant turn from %s; check_cases.py will reject a row citing this trace"
              % ", ".join(trace.SOURCE_MODELS), file=sys.stderr)
    print("%s@%s" % (t["session_id"], t["digest"][: trace.DIGEST_LEN]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
