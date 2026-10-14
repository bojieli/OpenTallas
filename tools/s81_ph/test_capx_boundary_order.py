"""Exercise the actual boundary Tcl at generated and legacy CTS call sites."""
import pathlib, subprocess, unittest
ROOT = pathlib.Path(__file__).resolve().parents[2]
MOCK = r'''
set root @ROOT@
set propagated @PROP@
set clocks {core_clk}
proc get_clocks {args} {if {[llength $args] == 0} {return $::clocks}; return [lindex $args end]}
proc all_clocks {} {return $::clocks}
proc get_property {p key} {
 if {$key eq "period"} {return 833.333}
 if {$key eq "is_propagated"} {return $::propagated}
 if {$key eq "arrival_max_rise"} {return [expr {[string match ser* $p] ? 200.0 : 100.0}]}
 if {$key eq "arrival_min_rise"} {return [expr {[string match ser* $p] ? 160.0 : 80.0}]}
 error "unmocked property $key"
}
proc get_ports {args} {return [lindex $args end]}
proc all_registers {args} {return [list [lindex $args end]]}
proc create_clock {args} {lappend ::clocks [lindex $args 1]}
foreach name {set_clock_uncertainty unset_input_delay unset_output_delay set_false_path set_input_delay} {proc $name {args} {}}
proc set_output_delay {args} {puts "OT_BOUNDARY_DELAY $args"}
proc set_propagated_clock {args} {set ::propagated 1}
namespace eval sta {proc worst_slack_cmd {args} {return 0}}
rename source real_source
proc source {p} {real_source [string map [list /src $::root] $p]}
proc clock_tree_synthesis {args} {set ::propagated 1}
proc read_sdc {args} {}
@QDM@
puts OT_SOURCE_BEGIN
real_source [file join $root physical/s81_ph_views/capture/x8_dual_boundary.tcl]
puts OT_SOURCE_END
@CALL@
'''
class Order(unittest.TestCase):
 def run_mode(self, prop, qdm, call):
  script = MOCK.replace('@ROOT@', '{'+str(ROOT)+'}').replace('@PROP@',str(prop)).replace('@QDM@', 'proc qdm_cts_orig {args} {}' if qdm else '').replace('@CALL@',call)
  result = subprocess.run(['tclsh'],input=script,text=True,capture_output=True)
  self.assertEqual(result.returncode,0,result.stderr)
  self.assertEqual(result.stderr,'')
  self.assertIn('CAPX_BOUNDARY core 100.0/80.0 serial 200.0/160.0',result.stdout)
  self.assertIn('-clock ser_clk',result.stdout)
  return result.stdout
 def test_generated_post_tree_hook_applies_during_first_source(self):
  out=self.run_mode(1,True,'')
  self.assertLess(out.index('CAPX_BOUNDARY'),out.index('OT_SOURCE_END'))
 def test_legacy_pre_tree_hook_defers_until_tree_exists(self):
  out=self.run_mode(0,True,'clock_tree_synthesis')
  self.assertGreater(out.index('CAPX_BOUNDARY'),out.index('OT_SOURCE_END'))
 def test_fresh_grt_session_applies_boundary(self):
  out=self.run_mode(1,False,'')
  self.assertLess(out.index('CAPX_BOUNDARY'),out.index('OT_SOURCE_END'))
if __name__ == '__main__':unittest.main()
