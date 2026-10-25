"""Exercise the real Tcl entry point with fake STA paths and a repair spy."""
import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).with_name("orfs_hold_mm.tcl")


class HoldStructuralGate(unittest.TestCase):
    def run_case(self, worst, failures, args, guard=1):
        script = r'''
source @HELPER@
set ::ot_mm_synced 1
set ::env(OT_HOLD_GUARD) @GUARD@
set ::env(REPORTS_DIR) @REPORTS@
set ::worst @WORST@
set ::failures @FAILURES@
set ::repairs {}
proc find_timing_paths {args} {
  if {[lsearch -exact $args -scenes] < 0 || [lindex $args [expr {[lsearch -exact $args -scenes]+1}]] ne "BC"} { error "must measure FF scene BC" }
  if {[lsearch -exact $args -slack_max] >= 0} {
    if {[lindex $args [expr {[lsearch -exact $args -slack_max]+1}]] != 0} { error "must count true failures, not margin" }
    return [lrepeat $::failures failing_path]
  }
  return worst_path
}
proc get_property {p prop} { if {$p eq "worst_path"} { return $::worst }; return -1 }
proc log_cmd {args} { lappend ::repairs $args }
# In passing cases finish after proving that repair is reached, avoiding the
# unrelated iterative guard (which needs a changing timing database).
rename ot_hm_guard saved_hm_guard
proc ot_hm_guard {args} { return -code error REPAIR_REACHED }
set code [catch {ot_repair_timing {@ARGS@}} msg options]
puts "RESULT $code $msg"
puts "REPAIRS $::repairs"
'''
        with tempfile.TemporaryDirectory() as directory:
            script = (script.replace('@HELPER@', '{'+str(HELPER)+'}')
                      .replace('@GUARD@', str(guard))
                      .replace('@REPORTS@', '{'+directory+'}')
                      .replace('@WORST@', str(worst))
                      .replace('@FAILURES@', str(failures))
                      .replace('@ARGS@', args))
            result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
            return result.stdout, result.stderr

    def test_bad_wns_stops_combined_before_hold(self):
        out, err = self.run_case(-100.01, 1, '-hold_margin 5')
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIRS {repair_timing -hold_margin 5 -setup}', out)
        self.assertNotIn('REPAIR_REACHED', out)
        self.assertEqual(err, '')

    def test_true_endpoint_threshold_and_direct_hold(self):
        out, _ = self.run_case(-1, 2001, '-hold -hold_margin 5')
        self.assertIn('2001 true failing endpoints', out)
        self.assertIn('REPAIRS \n', out)

    def test_threshold_inclusive_and_margin_flood_does_not_count(self):
        out, _ = self.run_case(-100, 2000, '-hold -hold_margin 50')
        self.assertNotIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIR_REACHED', out)

    def test_legacy_guard_disable_cannot_bypass_structural_stop(self):
        out, _ = self.run_case(-226.76, 16753, '-hold_margin 10', guard=0)
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIRS \n', out)

    def test_setup_only_unaffected(self):
        out, _ = self.run_case(-500, 200000, '-setup')
        self.assertNotIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIRS {repair_timing -setup}', out)


if __name__ == '__main__':
    unittest.main()
