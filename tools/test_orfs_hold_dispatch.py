"""Exercise production Tcl dispatch and guarded hold with a finite mock database."""
from pathlib import Path
import subprocess
import unittest

HELPER = Path(__file__).with_name("orfs_hold_mm.tcl")


class HoldDispatch(unittest.TestCase):
    def run_case(self, args, guard=None, native_error='', extra='', timed=False):
        script = r'''
source {@HELPER@}
@GUARD@
set ::calls {}
set ::events {}
set ::native_error {@ERROR@}
proc ot_rc_cal_hold {body} {
  lappend ::events rc_enter
  try {uplevel 1 $body} finally {lappend ::events rc_leave}
}
proc ot_hold_repair_scope {body} {
  lappend ::events scope_enter
  try {uplevel 1 $body} finally {lappend ::events scope_leave}
}
proc ot_hold_structural_gate {} {lappend ::events structural}
proc ot_hm_guard {args} {lappend ::events margin; return [lindex $args 0]}
proc ot_hold_stop {args} {return 0}
proc ot_hold_stats {} {return {10.236 0.0 0}}
namespace eval ord {proc get_db_block {} {return mock_block}}
proc mock_block {method} {
  if {$method ne "getInsts"} {error "unexpected database call $method"}
  return [lrepeat 10000 inst]
}
proc log_cmd {args} {
  lappend ::calls $args
  if {$::native_error ne ""} {error $::native_error}
}
@EXTRA@
set code [catch {ot_repair_timing {@ARGS@}} msg]
puts "CODE $code MSG $msg"
puts "CALLS $::calls"
puts "EVENTS $::events"
'''
        if timed:
            extra += r'''
set ::fixture_time 0
rename clock fixture_real_clock
proc clock {sub args} {
  if {$sub eq "seconds"} {incr ::fixture_time 20000; return $::fixture_time}
  return [fixture_real_clock $sub {*}$args]
}
set ::fixture_stats {{-10 -100 10} {-5 -50 5} {25 0 0}}
proc ot_hold_stats {} {
  set v [lindex $::fixture_stats 0]
  if {[llength $::fixture_stats] > 1} {set ::fixture_stats [lrange $::fixture_stats 1 end]}
  return $v
}
'''
        script = (script.replace('@HELPER@', str(HELPER))
                  .replace('@GUARD@', '' if guard is None else f'set ::env(OT_HOLD_GUARD) {guard}')
                  .replace('@ERROR@', native_error).replace('@EXTRA@', extra).replace('@ARGS@', args))
        result = subprocess.run(['tclsh'], input=script, text=True, capture_output=True, check=True)
        self.assertEqual(result.stderr, '')
        return result.stdout

    def test_explicit_hold_uses_existing_buffer_chunk_without_duplicate_selector(self):
        out = self.run_case('-setup_margin 30 -hold_margin 20 -hold -max_buffer_percent 100 -verbose')
        self.assertIn('OT_HOLD_GUARD start:', out)
        self.assertIn('margin chase stalled, stop', out)
        self.assertIn('CALLS {repair_timing -setup_margin 30 -hold_margin 20 -max_buffer_percent 20.000000 -verbose -hold}', out)
        self.assertIn('EVENTS rc_enter scope_enter structural margin scope_leave rc_leave', out)
        self.assertIn('CODE 0 MSG', out)

    def test_guard_zero_preserves_exact_uncapped_explicit_call(self):
        out = self.run_case('-setup_margin 30 -hold_margin 20 -hold -max_buffer_percent 100 -verbose', guard=0)
        self.assertNotIn('OT_HOLD_GUARD start:', out)
        self.assertIn('CALLS {repair_timing -setup_margin 30 -hold_margin 20 -hold -max_buffer_percent 100 -verbose}', out)
        self.assertIn('EVENTS rc_enter structural scope_enter margin scope_leave rc_leave', out)
        self.assertNotIn('-max_iterations', out)

    def test_setup_stays_outside_hold_scopes(self):
        out = self.run_case('-setup -setup_margin 30 -max_buffer_percent 100')
        self.assertIn('CALLS {repair_timing -setup -setup_margin 30 -max_buffer_percent 100}', out)
        self.assertIn('EVENTS \n', out)
        self.assertNotIn('OT_HOLD_GUARD', out)

    def test_combined_and_default_keep_existing_phase_order_and_options(self):
        for selectors in ('', '-setup -hold '):
            with self.subTest(selectors=selectors):
                out = self.run_case(selectors+'-setup_margin 30 -hold_margin 20 -max_buffer_percent 100')
                self.assertIn('CALLS {repair_timing -setup_margin 30 -hold_margin 20 -max_buffer_percent 100 -setup} {repair_timing -setup_margin 30 -hold_margin 20 -max_buffer_percent 20.000000 -hold}', out)
                self.assertIn('EVENTS rc_enter scope_enter structural margin scope_leave rc_leave', out)

    def test_combined_guard_off_keeps_original_unbounded_calls(self):
        out = self.run_case('-setup -hold -hold_margin 20 -max_buffer_percent 100', guard=0)
        self.assertIn('CALLS {repair_timing -hold_margin 20 -max_buffer_percent 100 -setup} {repair_timing -hold_margin 20 -max_buffer_percent 100 -hold}', out)
        self.assertNotIn('-max_iterations', out)

    def test_explicit_native_iteration_option_is_opt_in(self):
        out = self.run_case('-hold -hold_margin 20 -max_buffer_percent 100', extra='set ::env(OT_HOLD_CHUNK) 7')
        self.assertIn('-hold -max_iterations 7}', out)

    def test_default_has_no_added_iteration_or_wall_cap(self):
        out = self.run_case('-hold -hold_margin 20 -max_buffer_percent 100', timed=True)
        self.assertNotIn('-max_iterations', out)
        self.assertNotIn('OT_HOLD_TIMELOG', out)
        self.assertIn('chunk 2:', out)
        self.assertIn('hold ws 25.00', out)
        self.assertIn('CODE 0 MSG', out)

    def test_explicit_time_threshold_is_still_informational_only(self):
        out = self.run_case('-hold -hold_margin 20 -max_buffer_percent 100', timed=True,
                            extra='set ::env(OT_HOLD_MAX_HOURS) 1')
        self.assertIn('NO CAP, repair continues', out)
        self.assertIn('chunk 2:', out)
        self.assertIn('hold ws 25.00', out)
        self.assertIn('CODE 0 MSG', out)

    def test_explicit_total_buffer_bound_failure_propagates(self):
        out = self.run_case('-hold -hold_margin 20 -max_buffer_percent 1', native_error='RSZ-0060 Max buffer count')
        self.assertIn('CODE 1 MSG RSZ-0060 Max buffer count', out)
        self.assertNotIn('margin chase stalled, stop', out)
        self.assertNotIn('chunk buffer caps reached', out)

    def test_native_failure_propagates_and_both_scopes_restore(self):
        out = self.run_case('-hold -hold_margin 20 -max_buffer_percent 100', native_error='actual-native-failure')
        self.assertIn('CODE 1 MSG actual-native-failure', out)
        self.assertIn('scope_leave rc_leave', out)
        self.assertNotIn('margin chase stalled, stop', out)


if __name__ == '__main__':
    unittest.main()
