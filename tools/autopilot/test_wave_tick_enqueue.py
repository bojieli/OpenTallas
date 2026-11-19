"""WAVE-TICK-1119 (COORD 1): collect / retry_enqueue publish every row that passes in ONE coord commit"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from test_kit_wave import KW, cfg
from test_kit_wave_enqueue_retry import AP, EnqueueRetry, DENIED


class Batch(EnqueueRetry):
    def test_deferred_rows_go_in_one_batch_call(self):
        c = cfg(); a = self.rec("a"); b = self.rec("b"); d = self.rec("d")
        out = "enqueue: 3 row(s) PUBLISHED\nROW 0 OK ida\nROW 1 OK idb\nROW 2 ERR enqueue: REFUSED: bad row"
        ap = AP(self.d, [(0, out, "")]); st = self.st(a, b, d); n = {}
        c["_enqueue_defer"] = []
        for r in (a, b, d):
            KW.enqueue_pass(ap, c, st, r, n)
        self.assertEqual(ap.calls, [])                       # nothing published while deferring
        self.assertEqual(KW.flush_enqueues(ap, c, st, n), 3)
        self.assertEqual(len(ap.calls), 1)
        self.assertEqual(ap.calls[0][2], "--batch")
        self.assertEqual((a["status"], b["status"], d["status"]), ("ENQUEUED", "ENQUEUED", "FAIL"))
        self.assertEqual(d["class"], "FLOW")
        self.assertEqual(st["pass_n"], 2)
        self.assertNotIn("_enqueue_defer", c)

    def test_failed_publish_keeps_every_row_pass(self):
        c = cfg(); a = self.rec("a"); b = self.rec("b")
        ap = AP(self.d, [(1, "enqueue: NOT SUBMITTED: denied", "")]); st = self.st(a, b); n = {}
        c["_enqueue_defer"] = []
        KW.enqueue_pass(ap, c, st, a, n); KW.enqueue_pass(ap, c, st, b, n)
        KW.flush_enqueues(ap, c, st, n)
        self.assertEqual((a["status"], b["status"]), ("PASS", "PASS"))
        self.assertTrue(a["enqueue_pending"] and b["enqueue_pending"])

    def test_single_row_uses_the_single_path(self):
        c = cfg(); a = self.rec("a"); ap = AP(self.d, [(0, "", "")]); st = self.st(a)
        c["_enqueue_defer"] = []
        KW.enqueue_pass(ap, c, st, a, {})
        KW.flush_enqueues(ap, c, st, {})
        self.assertNotIn("--batch", ap.calls[0]); self.assertEqual(a["status"], "ENQUEUED")

    def test_retry_enqueue_publishes_pending_rows_together(self):
        c = cfg(); a = self.rec("a", enqueue_pending=1); b = self.rec("b", enqueue_pending=1)
        ap = AP(self.d, [(0, "ROW 0 OK x\nROW 1 OK y", "")]); st = self.st(a, b)
        self.assertEqual(KW.retry_enqueue(ap, c, st, {}), 2)
        self.assertEqual(len(ap.calls), 1)
        self.assertEqual((a["status"], b["status"]), ("ENQUEUED", "ENQUEUED"))


class BatchCli(unittest.TestCase):
    def test_batch_main_reports_rows_and_one_publish(self):
        import enqueue as E
        import queue_publish
        pub = []
        old = queue_publish.publish
        queue_publish.publish = lambda coord, line, msg, **k: pub.append((line, msg)) or "f" * 40
        good = ["--die", "qwen_kvsys", "--type", "t1", "--kit", "h:/srv/opentallas-scratch2/claude/l/k", "--src", "main@" + "a" * 40, "--geom", "PASS", "--geom-ref", "r", "--mem", "8", "--cells", "1000", "--lane", "L"]
        bad = ["--die", "qwen_kvsys", "--type", "t\t2", "--kit", "h:/k", "--src", "s", "--geom", "PASS", "--geom-ref", "r", "--mem", "8", "--cells", "1", "--lane", "L"]
        with tempfile.TemporaryDirectory() as t:
            f = Path(t) / "b.json"; f.write_text(json.dumps([good, bad]))
            import io, contextlib
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf):
                    rc = E.batch_main(str(f))
            finally:
                queue_publish.publish = old
        self.assertEqual(rc, 0); self.assertEqual(len(pub), 1)
        self.assertEqual(pub[0][0].count("\n"), 0)           # one valid row published
        o = buf.getvalue()
        self.assertIn("ROW 0 OK", o); self.assertIn("ROW 1 ERR", o)


if __name__ == "__main__":
    unittest.main()
