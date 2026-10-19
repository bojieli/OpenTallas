"""cts_native_probe.py probe script: path_classes.tcl helpers sourced relative to [info script] are inlined.

The probe runs its prelude as /probe.tcl inside the ORFS container, so a `source [file join [file dirname [file normalize
[info script]]] cross_clock_paths.tcl]` in path_classes.tcl resolved to /cross_clock_paths.tcl, which is not mounted
(S81-CAPRT / HKV-ERTAP 2026-10-19: the probe failed with an ORD error before STA).  The probe now inlines the helper.
"""
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import cts_native_probe as C  # noqa: E402


class ProbeTclTest(unittest.TestCase):
    def test_real_prelude_has_no_script_relative_source(self):
        tcl = C.probe_tcl()
        self.assertNotIn("info script", tcl)
        self.assertNotIn("/cross_clock_paths.tcl", tcl)
        # the helper's own text is present, once, before the probe's own command
        helper = (HERE / "cross_clock_paths.tcl").read_text().rstrip("\n")
        self.assertEqual(tcl.count(helper), 1)
        self.assertLess(tcl.index(helper), tcl.index("write_timing_model"))
        # the path-class procs are not part of the prelude
        self.assertNotIn("proc kind", tcl)

    def test_fixture_inlines_and_refuses(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "helper_a.tcl").write_text("proc ha {} { return 1 }\n")
            (d / "path_classes.tcl").write_text(
                "# head\n"
                "source [file join [file dirname [file normalize [info script]]] helper_a.tcl]\n"
                "  source [file join [file dirname [file normalize [info script]]] helper_a.tcl]  \n"
                "set x 1\nproc kind {} {}\n")
            tcl = C.probe_tcl(d)
            self.assertEqual(tcl.count("proc ha {} { return 1 }"), 2)
            self.assertNotIn("info script", tcl)
            self.assertIn("set x 1", tcl)
            # a missing helper fails loudly instead of running a probe that dies in the container
            (d / "path_classes.tcl").write_text(
                "source [file join [file dirname [file normalize [info script]]] gone.tcl]\nproc kind {} {}\n")
            with self.assertRaises(FileNotFoundError):
                C.probe_tcl(d)
            # an unsupported [info script] form is refused, never shipped
            (d / "path_classes.tcl").write_text("source [file dirname [info script]]/helper_a.tcl\nproc kind {} {}\n")
            with self.assertRaises(RuntimeError):
                C.probe_tcl(d)


class CoverageTest(unittest.TestCase):
    def test_child_flop_reference_is_measured(self):
        self.assertTrue(C.measured_coverage({"clk": {"src": "insertion.json boundary mean"}}))
        self.assertTrue(C.measured_coverage({"clk": {"src": "insertion.json child_flop boundary mean"}}))
        self.assertFalse(C.measured_coverage({"clk": {"src": "lib midrange"}}))
        self.assertFalse(C.measured_coverage({"clk": {"src": "insertion.json boundary mean"}, "ck2": {"src": "lib midrange"}}))
        self.assertFalse(C.measured_coverage({}))


if __name__ == "__main__":
    unittest.main()
