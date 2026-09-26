#!/usr/bin/env python3
"""Check that every CASES.md evidence row cites a real trace (the "never invent a row" rule).

    python3 tools/check_cases.py                       # format check; digest check if based/traces/ exists
    python3 tools/check_cases.py --traces based/traces --require-traces

A real row's Session cell must be `<session-id>@<digest12>` as printed by extract_trace.py.
When the trace directory is present, the cited file must exist and its events must still
hash to the cited digest. CI has no traces (they are gitignored), so it checks format only.
Exit 1 on any failure. Stdlib only.
"""
import argparse
import glob
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trace  # noqa: E402

PLACEHOLDER = "_awaiting case runs_"
SESSION_RE = re.compile(r"^`?([A-Za-z0-9][A-Za-z0-9_-]*)@([0-9a-f]{%d})`?$" % trace.DIGEST_LEN)


def rows(path):
    """Yield (line_no, cells) for each data row of the evidence table."""
    in_table = False
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            s = line.strip()
            if not s.startswith("|"):
                in_table = False
                continue
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells[:2] == ["Case", "Session"]:
                in_table = True
                continue
            if in_table and not all(set(c) <= set("-: ") for c in cells):
                yield n, cells


def check_file(path, traces_dir):
    errs = []
    real = placeholder = 0
    cache = {}
    for n, cells in rows(path):
        where = "%s:%d" % (path, n)
        if cells[0] == PLACEHOLDER:
            placeholder += 1
            continue
        real += 1
        if len(cells) < 2:
            errs.append("%s: row has no Session cell" % where)
            continue
        m = SESSION_RE.match(cells[1])
        if not m:
            errs.append("%s: Session cell %r is not <session-id>@<%d hex digest> (run tools/extract_trace.py)"
                        % (where, cells[1], trace.DIGEST_LEN))
            continue
        if traces_dir is None:
            continue
        sid, cited = m.groups()
        tpath = os.path.join(traces_dir, sid + ".json")
        if not os.path.isfile(tpath):
            errs.append("%s: cited trace %s does not exist" % (where, tpath))
            continue
        if tpath not in cache:
            t = trace.load(tpath)
            actual = trace.digest(t.get("events", []))
            stored = t.get("digest", "")
            cache[tpath] = actual if actual == stored else None
        actual = cache[tpath]
        if actual is None:
            errs.append("%s: %s was edited after extraction (stored digest != events)" % (where, tpath))
        elif not actual.startswith(cited):
            errs.append("%s: cites digest %s but %s hashes to %s"
                        % (where, cited, tpath, actual[: trace.DIGEST_LEN]))
    if real and placeholder:
        errs.append("%s: placeholder row still present next to %d real row(s)" % (path, real))
    return errs, real


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", default=".", help="repo root (default: .)")
    ap.add_argument("--traces", default=None, help="trace dir (default: <root>/based/traces if it exists)")
    ap.add_argument("--require-traces", action="store_true", help="fail if the trace dir is missing")
    args = ap.parse_args(argv)

    traces_dir = args.traces or os.path.join(args.root, "based", "traces")
    if not os.path.isdir(traces_dir):
        if args.require_traces:
            print("FAIL  trace dir %s not found" % traces_dir)
            return 1
        traces_dir = None

    files = sorted(glob.glob(os.path.join(args.root, "skills", "*", "CASES.md")))
    fail = total = 0
    for f in files:
        errs, real = check_file(f, traces_dir)
        total += real
        for e in errs:
            print("FAIL  " + e)
        fail += len(errs)
    mode = "digest-checked against %s" % traces_dir if traces_dir else "format only (no trace dir)"
    print("checked %d evidence row(s) in %d CASES.md, %s" % (total, len(files), mode))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
