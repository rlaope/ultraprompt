"""python3 -m unittest discover -s tools/tests"""
import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import check_cases  # noqa: E402
import extract_trace  # noqa: E402
import trace  # noqa: E402

FIXTURE = os.path.join(HERE, "fixtures", "session.jsonl")
HEADER = "| Case | Session | Task / domain | Distinctness shown vs existing axes | What it confirmed / contradicted / refined |\n|---|---|---|---|---|\n"


def quiet(fn, *a):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        rc = fn(*a)
    return rc, out.getvalue()


class ExtractTest(unittest.TestCase):
    def test_events_and_stats(self):
        t = extract_trace.build(FIXTURE)
        self.assertEqual(t["session_id"], "0000aaaa-fixture")
        self.assertEqual(t["model"], "claude-fable-5-1")
        kinds = [e["kind"] for e in t["events"]]
        # summary, isMeta, the duplicated uuid u3 and the non-JSON line are all dropped
        self.assertEqual(kinds, ["prompt", "thinking", "tool_call", "tool_result",
                                 "tool_call", "tool_result", "text"])
        self.assertEqual(t["events"][3]["tool"], "Bash")
        self.assertTrue(t["events"][3]["is_error"])
        self.assertEqual(t["events"][3]["text"], "1 failed")
        self.assertTrue(t["events"][4]["sidechain"])
        self.assertEqual(t["stats"]["tool_errors"], 1)
        self.assertEqual(t["stats"]["tools"], {"Bash": 1, "Edit": 1})
        self.assertEqual(t["stats"]["first_edit_seq"], 4)
        self.assertEqual(t["digest"], trace.digest(t["events"]))


class CheckCasesTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.traces = os.path.join(self.root, "based", "traces")
        rc, out = quiet(extract_trace.main, [FIXTURE, "--out-dir", self.traces])
        self.assertEqual(rc, 0)
        self.cite = out.strip()
        os.makedirs(os.path.join(self.root, "skills", "demo"))

    def tearDown(self):
        shutil.rmtree(self.root)

    def write_cases(self, *rows):
        with open(os.path.join(self.root, "skills", "demo", "CASES.md"), "w") as fh:
            fh.write("# demo\n\n" + HEADER + "".join("| %s |\n" % " | ".join(r) for r in rows))

    def run_check(self, *extra):
        return quiet(check_cases.main, ["--root", self.root, *extra])

    def test_placeholder_only_passes(self):
        self.write_cases(["_awaiting case runs_", "—", "—", "—", "—"])
        self.assertEqual(self.run_check()[0], 0)

    def test_cited_trace_passes(self):
        self.write_cases(["C01", "`%s`" % self.cite, "x", "y", "z"])
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)
        self.assertIn("digest-checked", out)

    def test_invented_row_fails(self):
        self.write_cases(["C01", "some session I remember", "x", "y", "z"])
        self.assertEqual(self.run_check()[0], 1)

    def test_missing_trace_fails(self):
        self.write_cases(["C01", "deadbeef@0123456789ab", "x", "y", "z"])
        self.assertEqual(self.run_check()[0], 1)

    def test_wrong_digest_fails(self):
        sid = self.cite.split("@")[0]
        self.write_cases(["C01", sid + "@000000000000", "x", "y", "z"])
        self.assertEqual(self.run_check()[0], 1)

    def test_edited_trace_fails(self):
        self.write_cases(["C01", self.cite, "x", "y", "z"])
        path = os.path.join(self.traces, self.cite.split("@")[0] + ".json")
        t = trace.load(path)
        t["events"][1]["text"] = "rewritten after the fact"
        with open(path, "w") as fh:
            json.dump(t, fh)
        self.assertEqual(self.run_check()[0], 1)

    def test_placeholder_next_to_real_row_fails(self):
        self.write_cases(["_awaiting case runs_", "—", "—", "—", "—"], ["C01", self.cite, "x", "y", "z"])
        self.assertEqual(self.run_check()[0], 1)

    def test_format_only_without_traces(self):
        shutil.rmtree(os.path.join(self.root, "based"))
        self.write_cases(["C01", self.cite, "x", "y", "z"])
        rc, out = self.run_check()
        self.assertEqual(rc, 0, out)
        self.assertIn("format only", out)
        self.assertEqual(self.run_check("--require-traces")[0], 1)


if __name__ == "__main__":
    unittest.main()
