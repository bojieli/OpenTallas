"""Causal Tcl tests for grouped CDC exceptions, without synthesis or STA builds.

The stub timing query models two actual launches into one endpoint. It deliberately
returns only the surviving launch for a bus query, as endpoint_path_count=1 allows.
Actual OpenSTA integration remains covered by test_gray_fifo_cdc_constraints.py.
"""
import ast
import os
from pathlib import Path
import subprocess
import unittest


SOURCE = Path(os.environ.get("TEST_GF_SOURCE", Path(__file__).with_name("gray_fifo_cdc_constraints.py")))


def verifier():
    tree = ast.parse(SOURCE.read_text())
    tcl = next(ast.literal_eval(node.value) for node in tree.body
               if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "TCL" for t in node.targets))
    return tcl[tcl.index("set ::ot_gf_pending {}"):tcl.index("proc ot_gf_crossing")]


STUB = r'''
namespace eval sta {proc object_type {obj} {return Cell}}
proc get_full_name {obj} {return $obj}
proc ot_gf_launch {obj} {return $obj}
proc ot_gf_role {obj} {return {mem fifo mem 0}}
proc ot_ce_finite {value} {expr {$value ne "INF"}}
set ::exceptions 0
proc set_max_delay {args} {incr ::exceptions}
proc set_min_delay {args} {incr ::exceptions}
proc get_property {path prop} {
  if {$prop eq "endpoint"} {return T}
  if {$path eq "bad"} {return INF}
  return 1.0
}
proc find_timing_paths {args} {
  set from [lindex $args [expr {[lsearch -exact $args -from]+1}]]
  if {$::mode eq "allnonfinite"} {return bad}
  # A grouped query returns L1's finite path and masks L2 at the same endpoint.
  if {[llength $from] > 1 || $from eq "L1"} {return good}
  set kind [lindex $args [expr {[lsearch -exact $args -path_delay]+1}]]
  if {$::mode eq "missing" || ($::mode eq "missing_min" && $kind eq "min")} {return {}}
  if {$::mode eq "nonfinite"} {return bad}
  return good
}
'''


class GroupedProof(unittest.TestCase):
    def run_case(self, mode, hold=False, active=False):
        script = STUB + verifier() + "\nset ::mode " + mode + "\n"
        script += "unset -nocomplain ::env(OT_HOLD_MM)\n"
        if hold:
            script += "set ::env(OT_HOLD_MM) 1\n"
        if active:
            script += "set ::ot_mm_active 1\n"
        script += r'''
ot_gf_bound L1 T 773.333
ot_gf_bound L2 T 773.333
if {[catch {ot_gf_verify} message]} {
  puts "VERDICT FAIL $message"
} else {
  puts "VERDICT PASS"
}
puts "EXCEPTIONS $::exceptions"
'''
        result = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
        self.assertEqual(result.stderr, "", result.stderr)
        return result.stdout

    def test_distinct_input_ports_do_not_share_cartesian_exception(self):
        script = STUB + verifier() + "\nset ::mode finite\n"
        script += "namespace eval sta {proc object_type {obj} {return Port}}\n"
        script += "ot_gf_bound P1 T1 773.333\not_gf_bound P2 T2 773.333\n"
        script += "ot_gf_verify\nputs \"EXCEPTIONS $::exceptions\"\n"
        result = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
        self.assertEqual(result.stderr, "", result.stderr)
        self.assertIn("EXCEPTIONS 4", result.stdout)

    def test_two_finite_pairs_share_one_exception(self):
        log = self.run_case("finite")
        self.assertIn("VERDICT PASS", log)
        self.assertIn("EXCEPTIONS 2", log)  # one max and one min for the entire bus

    def test_missing_launch_is_not_masked_by_another_launch(self):
        self.assertIn("VERDICT FAIL OT_GF: missing finite bounded max path L2 -> T", self.run_case("missing"))

    def test_missing_min_launch_is_not_masked_by_another_launch(self):
        self.assertIn("VERDICT FAIL OT_GF: missing finite bounded min path L2 -> T", self.run_case("missing_min"))

    def test_nonfinite_launch_is_not_masked_by_another_launch(self):
        self.assertIn("VERDICT FAIL OT_GF: missing finite bounded max path L2 -> T", self.run_case("nonfinite"))

    def test_nonfinite_is_never_deferred(self):
        log = self.run_case("allnonfinite", hold=True)
        self.assertIn("VERDICT FAIL", log)
        self.assertNotIn("PATH_DEFERRED", log)

    def test_only_missing_paths_defer_before_mm(self):
        log = self.run_case("missing", hold=True)
        self.assertIn("VERDICT PASS", log)
        self.assertEqual(log.count("PATH_DEFERRED L2 -> T"), 2)
        self.assertIn("VERDICT FAIL", self.run_case("missing", hold=True, active=True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
