"""KW-FIX-17 11-05: DPL-0033 diamond legalizer fallback in prd_hook.tcl, exercised in tclsh with stub commands."""
import pathlib
import re
import subprocess
import unittest

HOOK = pathlib.Path(__file__).with_name("prd_hook.tcl")


def block():
    s = HOOK.read_text()
    m = re.search(r"^detailed_placement\n(# KW-FIX-17 11-05 \(DPL-0033.*?\n\})\n", s, re.S | re.M)
    assert m, "fallback block not found after the ECO detailed_placement"
    return m.group(1)


def run(fails, env_off=False):
    tcl = (("set ::env(OT_PRD_DIAMOND_FALLBACK) 0\n" if env_off else "") +
           "set ::fails %d\nset ::log {}\n" % fails +
           "proc check_placement {} { if {$::fails > 0} { incr ::fails -1; error DPL-0033 } }\n"
           "proc detailed_placement {args} { lappend ::log [concat dpl $args] }\n"
           "set rc [catch {\n" + block() + "\n} msg]\nputs \"RC $rc $msg\"\nputs \"LOG $::log\"\n")
    return subprocess.run(["tclsh"], input=tcl, text=True, capture_output=True, check=True).stdout


class DiamondFallback(unittest.TestCase):
    def test_clean_placement_no_fallback(self):
        out = run(0)
        self.assertIn("RC 0", out)
        self.assertIn("LOG \n", out)

    def test_overlap_fixed_by_diamond(self):
        out = run(1)
        self.assertIn("OT_PRD legalizer fallback: diamond after: DPL-0033", out)
        self.assertIn("RC 0", out)
        self.assertIn("LOG {dpl -use_diamond_legalizer}", out)

    def test_overlap_left_after_diamond_fails(self):
        out = run(2)
        self.assertIn("RC 1 OT_PRD FAIL: check_placement after the ECO legalization: DPL-0033", out)

    def test_opt_out(self):
        out = run(1, env_off=True)
        self.assertIn("RC 1 OT_PRD FAIL", out)
        self.assertIn("LOG \n", out)


if __name__ == "__main__":
    unittest.main()
