#!/usr/bin/env python3
"""KW-FIX-45 11-11: an ot-run / ot-heavy NOT RUN (usage text, admission refusal) spends no RETRY-INFRA attempt."""
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as kw

ADMIT = "ot-heavy: NOT RUN: no memory on devoted-wren within 120 s (need 34 GB)\n"


class T(unittest.TestCase):
    def test_detect(self):
        self.assertTrue(kw.tool_not_run(ADMIT))
        self.assertTrue(kw.tool_not_run("Usage: ot-run [options]\n"))
        self.assertFalse(kw.tool_not_run(ADMIT + "ot-run: RAN on epyc8\nexit 137"))
        self.assertFalse(kw.tool_not_run("yosys elaboration failed rc 137"))
        self.assertFalse(kw.tool_not_run(""))

    def test_free_requeue(self):
        r = {"class": "INFRA", "attempt": 5, "infra_base": 2, "status": "FAIL"}
        self.assertEqual(kw.infra_used(r), 3)
        self.assertTrue(kw.free_not_run(r, ADMIT, now=100.0))
        self.assertEqual((r["status"], r["infra_base"], r["notrun_free"], r["no_host_at"]), ("RETRY-INFRA", 3, 1, 100.0))
        self.assertEqual(kw.infra_used(r), 2)

    def test_not_infra_or_ran(self):
        r = {"class": "FLOW", "attempt": 5, "infra_base": 2, "status": "FAIL"}
        self.assertFalse(kw.free_not_run(r, ADMIT))
        r = {"class": "INFRA", "attempt": 5, "infra_base": 2, "status": "FAIL"}
        self.assertFalse(kw.free_not_run(r, ADMIT + "ot-run: RAN on x\n"))
        self.assertEqual(r["infra_base"], 2)

    def test_bounded(self):
        r = {"class": "INFRA", "attempt": 30, "infra_base": 0, "status": "FAIL"}
        n = 0
        while kw.free_not_run(r, ADMIT):
            n += 1
        self.assertEqual(n, kw.NOT_RUN_FREE_MAX)
        self.assertEqual(kw.infra_used(r), 30 - kw.NOT_RUN_FREE_MAX)


if __name__ == "__main__":
    unittest.main()
