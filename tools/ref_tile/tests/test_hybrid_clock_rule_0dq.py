"""OT_HYBRID glue-root clock rule = owner 2026-10-17 0dq (textbook_lint.clock_rule_eval):
FAIL only on pin-flop (child-flop on a landed parent) spread > 80 ps at TT or FF; > 15k sinks / > 300 ps insertion WARN.
Runs the generated Tcl proc under tclsh (no OpenROAD needed)."""
import re
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE

BODIES = dict(entries=CE.BODY, leaf=CE.LEAF_BODY, landed=CE.LANDED_BODY)


def proc_text(body):
    m = re.search(r"^proc ot_ce_clock_rule .*?^}\n", body, re.M | re.S)
    assert m, "ot_ce_clock_rule proc missing"
    return m.group(0)


@unittest.skipUnless(shutil.which("tclsh"), "tclsh required")
class ClockRuleProc(unittest.TestCase):
    def level(self, corner, sinks, all_mean, pin_mean, lo, hi, body=CE.BODY):
        tcl = proc_text(body) + f"puts RESULT=[ot_ce_clock_rule {corner} ck_sw {sinks} {all_mean} {pin_mean} {lo} {hi} boundary]\n"
        r = subprocess.run(["tclsh"], input=tcl, capture_output=True, text=True, check=True)
        self.assertIn("OT_HYBRID CLOCK_RULE", r.stdout)
        return re.search(r"RESULT=(\w+)", r.stdout).group(1), r.stdout

    def test_large_deep_tree_with_tight_pin_spread_passes_with_warn(self):
        # the COLL q2/q3 ck_sw shape: 62.9k flops, deep insertion, pin-flop spread inside 80 -> WARN, not FAIL
        for c in ("tt", "ff", "ss"):
            lvl, out = self.level(c, 62900, 420.0, 410.0, 380.0, 455.0)
            self.assertEqual(lvl, "WARN", out)
            self.assertIn("62900 > 15000", out)
            self.assertIn("> 300", out)

    def test_pin_spread_over_80_fails_at_tt_and_ff_only(self):
        for c, want in (("tt", "FAIL"), ("ff", "FAIL"), ("TT", "FAIL"), ("ss", "WARN")):
            self.assertEqual(self.level(c, 62900, 420.0, 410.0, 360.0, 441.0)[0], want, c)
        # sink count is not a criterion: a small root fails on spread alone too
        self.assertEqual(self.level("ff", 900, 120.0, 110.0, 60.0, 141.0)[0], "FAIL")

    def test_boundary_80_exact_passes(self):
        self.assertEqual(self.level("tt", 900, 120.0, 110.0, 60.0, 140.0)[0], "PASS")

    def test_insertion_alone_warns(self):
        self.assertEqual(self.level("tt", 900, 350.0, 340.0, 320.0, 360.0)[0], "WARN")
        self.assertEqual(self.level("ff", 20000, 100.0, 100.0, 80.0, 120.0)[0], "WARN")


class NoSinkOrInsertionHardFail(unittest.TestCase):
    def test_every_body_judges_spread_not_sinks(self):
        for name, body in BODIES.items():
            with self.subTest(body=name):
                self.assertNotIn("exceeds measured large-root", body)
                self.assertNotIn("exceeds boundary insertion limit", body)
                self.assertNotRegex(body, r"if \{\[llength \$(pins|arrivals)\] > 15000 &&")
                self.assertEqual(body.count("ot_ce_clock_rule $corner $name"), 1)
        for name in ("entries", "leaf"):          # leaf / hybrid tiles: the boundary-register spread aborts the flow
            self.assertEqual(BODIES[name].count(CE.RULE_ABORT), 1, name)
        # a landed parent reports the whole-root span; its verdict is per linked child pair (pre_route_gate)
        self.assertNotIn('pin-flop spread [format', CE.LANDED_BODY)
        self.assertIn("OT_LANDED CLOCK_RULE_SPAN", CE.LANDED_BODY)

    def test_landed_child_flop_extent_is_judged(self):
        # landed parents widen lo/hi with the child-flop extents BEFORE the rule is applied
        b = CE.LANDED_BODY
        self.assertLess(b.index("set lo [expr {min($lo, $clo)}]"), b.index("ot_ce_clock_rule $corner $name"))


if __name__ == "__main__":
    unittest.main()
