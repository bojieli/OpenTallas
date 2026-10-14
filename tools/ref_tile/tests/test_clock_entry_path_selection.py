"""Exercise the generated Tcl clock-path selector without an OpenROAD database.

Physical WC/BC probes remain required: these regressions cover path eligibility
and fail-closed behavior, using only mocked OpenSTA object interfaces.
"""
import pathlib
import subprocess
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import clock_entry_constraints as CE


# Load the same procedures emitted into generated SDCs, without applying an
# entire parent constraint set to this intentionally minimal object graph.
PROCEDURES = CE.BODY.rsplit("\not_ce_apply\n", 1)[0]
MOCK_OPENSTA = r'''
namespace eval sta {}
proc sta::cmd_scene {} {return WC}
proc get_property {object property} {
  if {$object ne "WC" || $property ne "name"} {error "unexpected property query"}
  return WC
}
proc get_full_name {object} {return $object}
proc sta::time_sta_ui {seconds} {
  # Preserve the nonfinite sentinel that the C++ unit converter returns.
  if {[regexp -nocase {inf|nan} $seconds]} {return $seconds}
  return [expr {$seconds * 1.0e12}]
}
proc pin {method} {
  if {$method ne "vertices"} {error "unexpected pin method"}
  return {NULL vertex}
}
proc vertex {method rise maximum} {
  if {$method ne "path_iterator" || $rise ne "rise" || $maximum ne "max"} {
    error "selector must request rising maximum clock paths"
  }
  set ::cursor 0
  return paths
}
proc paths {method} {
  switch -- $method {
    has_next {return [expr {$::cursor < [llength $::test_paths]}]}
    next {
      set ::current_path [lindex $::test_paths $::cursor]
      incr ::cursor
      return path
    }
    finish {incr ::finished}
    default {error "unexpected iterator method"}
  }
}
proc path {method} {
  switch -- $method {
    arrival {return [lindex $::current_path 0]}
    tag {return [lindex $::current_path 1]}
    default {error "unexpected path method"}
  }
}
proc assert_equal {actual expected} {
  if {$actual ne $expected} {error "expected '$expected', got '$actual'"}
}
proc expect_missing {} {
  if {![catch {ot_ce_clock_wire pin ot_entry_58} message]} {
    error "missing or ambiguous clock path was accepted"
  }
  if {![string match {*missing unique finite propagated clock arrival*} $message]} {
    error "unexpected rejection: $message"
  }
}
set ::test_paths {}
set ::finished 0
'''


class ClockEntryPathSelector(unittest.TestCase):
    def run_tcl(self, body):
        script = (PROCEDURES + MOCK_OPENSTA + "\nproc test {} {\n" + body
                  + "\n}\nif {[catch {test} message]} {puts stderr $message; exit 1}\nputs PASS\n")
        run = subprocess.run(["tclsh"], input=script, text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertEqual(run.stderr, "")
        self.assertTrue(run.stdout.rstrip().endswith("PASS"), run.stdout)

    def test_finite_values_and_infinity_nan_sentinels(self):
        self.run_tcl(r'''
foreach value {0 -0.25 4.2e-3} {assert_equal [ot_ce_finite $value] 1}
foreach value {Inf +Inf -Inf INF -INF NaN nan not_a_number {}} {
  assert_equal [ot_ce_finite $value] 0
}
''')

    def test_one_matching_clock_path_and_unit_conversion(self):
        self.run_tcl(r'''
set ::test_paths {{1.84234e-13 {41454 WC ^max ot_entry_58 ^ (clock prop) clk_src clk_vm_port[0]}}}
assert_equal [ot_ce_clock_wire pin ot_entry_58] 0.184234
assert_equal $::finished 1
''')

    def test_other_scene_clock_edge_and_unpropagated_paths_are_excluded(self):
        self.run_tcl(r'''
set ::test_paths {
 {9e-12 {1 BC ^max ot_entry_58 ^ (clock prop)}}
 {9e-12 {2 WC ^max ot_entry_0 ^ (clock prop)}}
 {9e-12 {3 WC ^max ot_entry_58 ^ (clock ideal)}}
 {9e-12 {4 WC ^max ot_entry_58 v (clock prop)}}
 {9e-12 {5 WC ^min ot_entry_58 ^ (clock prop)}}
 {2.5e-13 {6 WC ^max ot_entry_58 ^ (clock prop)}}
}
assert_equal [ot_ce_clock_wire pin ot_entry_58] 0.25
assert_equal $::finished 1
''')

    def test_only_ineligible_paths_cannot_satisfy_final_measurement(self):
        self.run_tcl(r'''
set ::ot_ref_pre_cts 0
set ::ot_ce_require_wire 1
foreach tag {
 {1 BC ^max ot_entry_58 ^ (clock prop)}
 {2 WC ^max ot_entry_0 ^ (clock prop)}
 {3 WC ^max ot_entry_58 ^ (clock ideal)}
} {
 set ::test_paths [list [list 2.5e-13 $tag]]
 expect_missing
}
''')

    def test_multiple_matching_paths_rejected_even_before_cts(self):
        self.run_tcl(r'''
set ::test_paths {
 {2.5e-13 {1 WC ^max ot_entry_58 ^ (clock prop)}}
 {3e-13 {2 WC ^max ot_entry_58 ^ (clock prop)}}
}
set ::ot_ref_pre_cts 1
set ::ot_ce_require_wire 0
expect_missing
assert_equal $::finished 1
''')

    def test_nonfinite_matching_arrivals_rejected(self):
        self.run_tcl(r'''
set ::ot_ref_pre_cts 0
set ::ot_ce_require_wire 1
foreach value {Inf -Inf NaN} {
 set ::test_paths [list [list $value {1 WC ^max ot_entry_58 ^ (clock prop)}]]
 expect_missing
}
''')

    def test_pre_cts_diagnostic_requires_no_physical_wire_requirement(self):
        self.run_tcl(r'''
set ::ot_ref_pre_cts 1
assert_equal [ot_ce_clock_wire pin ot_entry_58] 0.0
set ::ot_ce_require_wire 0
assert_equal [ot_ce_clock_wire pin ot_entry_58] 0.0
set ::ot_ce_require_wire 1
expect_missing
set ::ot_ref_pre_cts 0
set ::ot_ce_require_wire 0
expect_missing
unset ::ot_ref_pre_cts
unset ::ot_ce_require_wire
expect_missing
''')


if __name__ == "__main__":
    unittest.main()
