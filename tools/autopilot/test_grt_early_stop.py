#!/usr/bin/env python3
"""FLOW-TIME-1 11-07: grt_early_stop.py stays off by default and stops only what its rule names"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import grt_early_stop as G  # noqa: E402

ENTRY = "violation type: Horizontal congestion\n\tcomment: capacity:0 usage:{u} congestion:{c}\n"


class Kit:
    def __init__(self, root):
        self.k = Path(root) / "kit"
        self.logs = self.k / "run/logs/asap7/d/base"
        self.reps = self.k / "run/reports/asap7/d/base"
        self.res = self.k / "run/results/asap7/d/base"
        for d in (self.logs, self.reps, self.res):
            d.mkdir(parents=True)
        (self.k / "config.mk").write_text("export MAX_ROUTING_LAYER = M7\n")
        (self.logs / "5_1_grt.log").write_text("[INFO GRT-0102] Start extra iteration 3/30\n")

    def report(self, n, overflow, entries=2):
        each = overflow // entries
        rest = overflow - each * entries
        t = [ENTRY.format(u=1, c=each + (rest if i == 0 else 0)) for i in range(entries)]
        (self.reps / f"congestion-{n}.rpt").write_text("".join(t))


class TestRule(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(G.parse_rule("15:10000, 20:1000"), {15: 10000, 20: 1000})
        for bad in ("", "15", "a:1", "15:1,"):
            with self.assertRaises(ValueError):
                G.parse_rule(bad)

    def test_decide_first_rule_met(self):
        r = {15: 10000, 20: 1000}
        self.assertIsNone(G.decide({5: 900000, 15: 9999}, r))
        self.assertEqual(G.decide({15: 10000}, r), (15, 10000, 10000))
        self.assertEqual(G.decide({15: 9999, 20: 1000}, r), (20, 1000, 1000))
        self.assertIsNone(G.decide({}, r))


class TestScan(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.kit = Kit(self.t.name)
        self.env = {"OT_GRT_EARLY_STOP": "15:10000,20:1000"}

    def no_find(self, kit):
        raise AssertionError("no process lookup expected")

    def test_off_without_env_reads_nothing(self):
        self.assertEqual(G.scan(["/nonexistent/kit"], act=True, env={}, find=self.no_find),
                         ["grt_early_stop: off (OT_GRT_EARLY_STOP unset)"])

    def test_shadow_changes_nothing(self):
        self.kit.report(15, 20000)
        out = G.scan([str(self.kit.k)], env=self.env, find=self.no_find)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("WOULD-STOP overflow 20000 >= 10000 at iteration 15"))
        self.assertFalse((self.kit.k / "grt_early_stop.json").exists())

    def test_act_flag_alone_does_not_act(self):
        self.kit.report(15, 20000)
        out = G.scan([str(self.kit.k)], act=True, env=self.env, find=self.no_find)
        self.assertTrue(out[0].startswith("WOULD-STOP"))

    def test_below_rule_silent(self):
        self.kit.report(15, 9999)
        self.kit.report(20, 999)
        self.assertEqual(G.scan([str(self.kit.k)], env=self.env), [])

    def test_allow_congestion_never_stopped(self):
        self.kit.report(15, 900000)
        (self.kit.k / "config.mk").write_text("export GLOBAL_ROUTE_ARGS = -congestion_report_iter_step 5 -verbose -allow_congestion\n")
        out = G.scan([str(self.kit.k)], act=True, env=dict(self.env, OT_GRT_EARLY_STOP_ACT="1"), find=self.no_find)
        self.assertEqual(len(out), 1)
        self.assertTrue(out[0].startswith("SKIP"))

    def test_stale_report_of_an_earlier_run_ignored(self):
        self.kit.report(15, 900000)
        old = time.time() - 3600
        os.utime(self.kit.reps / "congestion-15.rpt", (old, old))
        (self.kit.res / "4_cts.odb").write_text("x")
        self.assertEqual(G.scan([str(self.kit.k)], env=self.env), [])

    def test_after_global_route_returned_never_stopped(self):
        self.kit.report(15, 900000)
        (self.kit.logs / "5_1_grt.log").write_text("Took 900 seconds: global_route -congestion_iterations 30\n")
        self.assertEqual(G.scan([str(self.kit.k)], env=self.env), [])

    def test_act_stops_the_one_process_and_marks_the_class(self):
        self.kit.report(15, 20000)
        p = subprocess.Popen(["sleep", "300"])
        self.addCleanup(p.kill)
        self.addCleanup(p.wait)
        import threading
        threading.Thread(target=p.wait, daemon=True).start()
        out = G.scan([str(self.kit.k)], act=True, env=dict(self.env, OT_GRT_EARLY_STOP_ACT="1"), find=lambda k: [p.pid])
        self.assertTrue(out[0].startswith("STOPPED"), out)
        time.sleep(0.1)
        self.assertEqual(p.poll(), -15)
        self.assertIn("[ERROR GRT-0116] early stop", (self.kit.logs / "5_1_grt.log").read_text())
        self.assertIn('"iteration": 15', (self.kit.k / "grt_early_stop.json").read_text())

    def test_act_refuses_when_process_is_ambiguous(self):
        self.kit.report(15, 20000)
        env = dict(self.env, OT_GRT_EARLY_STOP_ACT="1")
        for pids in ([], [111111, 222222]):
            out = G.scan([str(self.kit.k)], act=True, env=env, find=lambda k: pids)
            self.assertTrue(out[0].startswith("NOT-STOPPED"), out)
        self.assertFalse((self.kit.k / "grt_early_stop.json").exists())


class TestReplay(unittest.TestCase):
    def row(self, e, reps, tot=(0,), drt=False, so=(), k="k"):
        return dict(k=k, e=e, el=1000.0, mt=2000.0, tot=list(tot), drt=drt, so=list(so), reps=[[n, 1500.0, 1, v] for n, v in reps])

    def test_counts(self):
        rows = [self.row("GRT-0116", [(15, 20000)], tot=(9,)),
                self.row("GRT-0116", [(15, 10), (20, 10)], tot=(9,)),
                self.row("", [(15, 20000)], tot=(0,), k="fp"),
                self.row("", [(20, 1000)], tot=(5,), k="other"),
                self.row("", [(15, 5)], tot=(0,))]
        r = G.replay_rows(rows, {15: 10000, 20: 1000})
        self.assertEqual((r["grt0116"], r["caught"], r["false_stops"], r["other"]), (2, 1, 1, 1))
        self.assertEqual(r["false_stop_kits"], ["fp"])
        self.assertAlmostEqual(r["saved_h"], 0.1)


if __name__ == "__main__":
    unittest.main()
