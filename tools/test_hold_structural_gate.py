"""Exercise the real Tcl entry point with fake STA paths and a repair spy."""
import pathlib
import subprocess
import tempfile
import unittest

HELPER = pathlib.Path(__file__).with_name("orfs_hold_mm.tcl")


class HoldStructuralGate(unittest.TestCase):
    def run_case(self, worst, failures, args, guard=1, synced=True, inputs=0, nports=0, planned=None):
        script = r'''
source @HELPER@
set ::ot_mm_synced @SYNCED@
set ::ot_mm_active 1
set ::env(OT_CLOCK_RC_CAL) 0
set ::env(OT_HOLD_GUARD) @GUARD@
set ::env(REPORTS_DIR) @REPORTS@
set ::worst @WORST@
set ::failures @FAILURES@
set ::inputs @INPUTS@
set ::nports @NPORTS@
@PLANNED@
set ::repairs {}
proc find_timing_paths {args} {
  if {[lsearch -exact $args -scenes] < 0 || [lindex $args [expr {[lsearch -exact $args -scenes]+1}]] ne "BC"} { error "must measure FF scene BC" }
  if {[lsearch -exact $args -slack_max] >= 0} {
    if {[lindex $args [expr {[lsearch -exact $args -slack_max]+1}]] != 0} { error "must count true failures, not margin" }
    return [concat [lrepeat $::inputs in_path] [lrepeat [expr {$::failures - $::inputs}] failing_path]]
  }
  return worst_path
}
proc get_ports {args} { set l {}; for {set i 0} {$i < $::nports} {incr i} { lappend l port_$i }; lappend l out_0; return $l }
proc get_full_name {x} { return $x }
proc get_property {p prop} {
  if {$prop eq "direction"} { return [expr {[string match port_* $p] ? "input" : "output"}] }
  if {$prop eq "startpoint"} { return [expr {$p eq "in_path" ? "port_0" : "u_reg/CLK"}] }
  if {$p eq "worst_path"} { return $::worst }; return -1
}
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
                      .replace('@SYNCED@', '1' if synced else '0')
                      .replace('@REPORTS@', '{'+directory+'}')
                      .replace('@WORST@', str(worst))
                      .replace('@FAILURES@', str(failures))
                      .replace('@ARGS@', args)
                      .replace('@INPUTS@', str(inputs))
                      .replace('@NPORTS@', str(nports))
                      .replace('@PLANNED@', '' if planned is None else 'set ::env(OT_HOLD_PLANNED_INPUT) %s' % planned))
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
        self.assertIn('REPAIRS {repair_timing -hold_margin 10 -setup}', out)

    def test_setup_only_unaffected(self):
        out, _ = self.run_case(-500, 200000, '-setup')
        self.assertNotIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIRS {repair_timing -setup}', out)

    def test_explicit_setup_and_hold_does_not_bypass(self):
        out, _ = self.run_case(-101, 1, '-setup -hold -hold_margin 5')
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIRS {repair_timing -hold_margin 5 -setup}', out)
        self.assertNotIn('REPAIR_REACHED', out)

    def test_unsynchronized_ff_fails_closed_even_if_primary_hold_passes(self):
        out, _ = self.run_case(20, 0, '-hold', synced=False)
        self.assertIn('synchronized FF scene BC unavailable', out)
        self.assertIn('REPAIRS \n', out)

    # FLOW-SHARED-5 (COORD S81-R24): planned input-hold demand counted apart from internal failures
    def test_planned_input_demand_does_not_count_as_structural(self):
        out, _ = self.run_case(-40, 2096, '-hold -hold_margin 5', inputs=1909, nports=2000)
        self.assertIn('OT_HOLD_PLANNED_INPUT stage=cts: internal 187 endpoints (ws -1.00), planned input 1909 endpoints', out)
        self.assertNotIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('REPAIR_REACHED', out)

    def test_input_endpoints_beyond_port_bits_are_structural(self):
        out, _ = self.run_case(-40, 2096, '-hold -hold_margin 5', inputs=1909, nports=1000)
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('planned input 1909 endpoints (ws -1.00) of 1000 input-port bits', out)
        self.assertNotIn('REPAIR_REACHED', out)

    def test_internal_count_still_limited(self):
        out, _ = self.run_case(-40, 4101, '-hold -hold_margin 5', inputs=2100, nports=4000)
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('internal 2001 endpoints', out)
        self.assertNotIn('REPAIR_REACHED', out)

    def test_worst_slack_limit_applies_to_input_paths_too(self):
        out, _ = self.run_case(-120, 2096, '-hold -hold_margin 5', inputs=2096, nports=4000)
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertIn('limits: ws >= -100 ps, endpoints <= 2000', out)
        self.assertNotIn('REPAIR_REACHED', out)

    def test_planned_split_can_be_disabled(self):
        out, _ = self.run_case(-40, 2096, '-hold -hold_margin 5', inputs=1909, nports=2000, planned=0)
        self.assertIn('OT_HOLD_STRUCTURAL', out)
        self.assertNotIn('OT_HOLD_PLANNED_INPUT', out)
        self.assertNotIn('REPAIR_REACHED', out)

    def test_split_not_run_when_total_within_limits(self):
        out, _ = self.run_case(-40, 1500, '-hold -hold_margin 5', inputs=1500, nports=0)
        self.assertNotIn('OT_HOLD_PLANNED_INPUT', out)
        self.assertIn('REPAIR_REACHED', out)


if __name__ == '__main__':
    unittest.main()
