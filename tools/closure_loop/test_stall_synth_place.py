"""SYNTH/PLACE STALL (coordinator 2026-10-10): a synth / place step > 4 h with no progress -> EARLY_FAIL_STALL."""
import time
import unittest
from unittest.mock import patch

import closure_loop as cl
import stuckscan as ss


def run(step, step_h, quiet_min, status="RUNNING"):
    now = time.time()
    b = dict(design="x", root="/r", current=step, logs=[("1_1_yosys_canonicalize.log", now - step_h * 3600, 1),
                                                        (step, now - quiet_min * 60, 9)], corner="TT")
    o = dict(bases=[b], fresh=now - quiet_min * 60, cpu_cores=8.0, pid_alive=True)
    j = dict(name="j", status=status, stage_key="route", spec={"block": "blk", "owner": "o"}, run="/r/j", host="h")
    with patch.object(ss, "gate_metrics", return_value=None), patch.object(ss, "hopeless", return_value=[]), \
            patch.object(ss, "redundant", return_value=(None, False)), patch.object(ss, "is_die_run", return_value=False):
        return ss.diagnose(j, o, {}, [j], set(), now)


class Stall(unittest.TestCase):
    def test_synth_quiet_over_4h_fails(self):
        d = run("1_2_yosys.tmp.log", 5, 120)
        self.assertEqual((d["action"], d.get("verdict")), ("early_fail", "EARLY_FAIL_STALL"))

    def test_place_over_8h_fails_even_if_logging(self):
        d = run("3_3_place_gp.tmp.log", 9, 1)
        self.assertEqual(d.get("verdict"), "EARLY_FAIL_STALL")

    def test_progressing_place_under_8h_runs(self):
        d = run("3_3_place_gp.tmp.log", 5, 1)
        self.assertNotEqual(d.get("verdict"), "EARLY_FAIL_STALL")

    def test_cts_not_affected(self):
        d = run("4_1_cts.tmp.log", 9, 120)
        self.assertNotEqual(d.get("verdict"), "EARLY_FAIL_STALL")

    def test_verdict_is_a_loop_early_fail(self):
        self.assertIn("EARLY_FAIL_STALL", cl.EARLY_FAIL)
        self.assertIn("EARLY_FAIL_STALL", cl.TERMINAL)


if __name__ == "__main__":
    unittest.main()
