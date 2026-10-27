"""FAIL-WITNESS AUTO-CAPTURE (GATE-FRICTION 2026-10-18): a mutant that failed as expected leaves its real log excerpt as
the witness; a mutant that did not fail captures nothing and stays a failed bench.  ssh is mocked."""
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import closure_loop as cl

LOG = "\n".join([f"cycle {i} ok" for i in range(500)] + ["MISMATCH lane 3 got 0x1 want 0x2", "errors=1"]
                + [f"tail {i}" for i in range(300)]) + "\n"


def job():
    return dict(name="t-abc1234", host="h", run="/r", stage_tag="b1", events=[], spec={})


class FailWitness(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.p = patch.object(cl, "WITNESS_DIR", Path(self.td.name))
        self.p.start()
        self.ev = patch.object(cl, "event", lambda j, m: j["events"].append(m))
        self.ev.start()

    def tearDown(self):
        self.p.stop()
        self.ev.stop()
        self.td.cleanup()

    def outcome(self, log, rc=1, rx=r"^MISMATCH\b"):
        j = job()
        st = dict(key="bench_mut", expect="fail", fail_regex=rx)
        with patch.object(cl, "ssh", lambda *a, **k: SimpleNamespace(returncode=0, stdout="OT_BENCH_LOG_READ\n" + log, stderr="")):
            return j, cl.bench_outcome(j, st, rc)

    def test_capture_on_expected_fail(self):
        j, ok = self.outcome(LOG)
        self.assertTrue(ok)
        w = j["fail_witnesses"]["bench_mut"]
        body = Path(w["path"]).read_text()
        self.assertRegex(body, re.compile(r"^MISMATCH\b", re.M))
        self.assertIn("line(s) omitted", body)          # excerpt, not the whole log
        self.assertLess(len(body), len(LOG))
        self.assertEqual(w["matched"], "MISMATCH")

    def test_no_capture_when_mutant_passes(self):
        j, ok = self.outcome("\n".join(f"cycle {i} ok" for i in range(50)) + "\nPASS\n", rc=0)
        self.assertFalse(ok)                          # still a failed negative control -> NEEDS_RTL upstream
        self.assertNotIn("fail_witnesses", j)

    def test_no_capture_without_regex(self):
        j = job()
        st = dict(key="bench_mut", expect="fail")
        with patch.object(cl, "ssh", lambda *a, **k: SimpleNamespace(returncode=0, stdout="OT_BENCH_LOG_READ\nFAIL x\n", stderr="")):
            self.assertTrue(cl.bench_outcome(j, st, 1))
        self.assertNotIn("fail_witnesses", j)

    def test_multiline_match_kept(self):
        txt = cl.witness_text("a\n" * 1000 + "BAD\nerrors=3\n" + "b\n" * 1000, r"BAD\nerrors=\d+")
        self.assertIsNotNone(txt)
        self.assertRegex(txt, r"BAD\nerrors=3")


if __name__ == "__main__":
    unittest.main()
