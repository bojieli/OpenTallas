"""KW-FIX-17 11-05: targeted PRD fanout cap (prd_autofo.tcl) on violator nets above OT_PRD_AUTO_FANOUT loads"""
import pathlib
import subprocess
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
STUB = r'''
set ::env(REPORTS_DIR) [lindex $argv 0]
source [lindex $argv 1]
# nets: name -> {loads dont_touch}
array set L {big 40 small 5 quiet 60 frozen 50}
array set dt {big 0 small 0 quiet 0 frozen 1}
foreach n {big small quiet frozen} {
 proc $n {method args} [string map [list @N@ $n] {
  switch $method {
   getSigType {return SIGNAL}
   isDoNotTouch {return $::dt(@N@)}
   getName {return @N@}
   setDoNotTouch {set ::dt(@N@) [lindex $args 0]}
   getITerms {set r {}; for {set i 0} {$i < $::L(@N@)} {incr i} {lappend r in}; lappend r drv; return $r}
   getBTerms {return {}}
  }
 }]
}
proc in {m} {return 1}
proc drv {m} {return 0}
namespace eval ord {proc get_db_block {} {return block}}
proc block {method} {return {big small quiet frozen}}
proc get_pins {args} {return [lindex $args end]}
proc get_ports {args} {return {}}
proc get_nets {args} {set p [lindex $args end]; return [lindex [split $p /] 0]}
proc get_full_name {arg} {return $arg}
proc report_check_types {args} {
 set f [open [lindex $args end] w]
 foreach p $::VIO { puts $f "$p/A 320.00 400.00 -80.00 (VIOLATED)" }
 close $f
}
set ::fo none
proc current_design {} {return top}
proc set_max_fanout {v d} {set ::fo $v}
set ::calls {}
proc repair_design {args} {
 lappend ::calls [list $::fo $::dt(big) $::dt(small) $::dt(quiet) $::dt(frozen)]
 if {$::fail} {error "native repair failure"}
}
'''
CASES = r'''
set fail 0
set VIO {big small frozen}
puts "R1 [ot_prd_auto_fanout {-slew_margin 20} 32] $calls fo=$fo dt=$dt(big)$dt(small)$dt(quiet)$dt(frozen)"
set calls {}; set VIO {small}
puts "R2 [ot_prd_auto_fanout {-slew_margin 20} 32] [llength $calls]"
set calls {}; set VIO {big}
puts "R3 [ot_prd_auto_fanout {-slew_margin 20} 0] [llength $calls]"
set fail 1; set VIO {big}
puts "R4 [catch {ot_prd_auto_fanout {-slew_margin 20} 32} m] $m fo=$fo dt=$dt(big)$dt(small)$dt(quiet)$dt(frozen)"
puts "R5 [catch {ot_prd_auto_fanout {} x} m]"
'''


class AutoFanout(unittest.TestCase):
    def run_tcl(self):
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "t.tcl"
            p.write_text(STUB + CASES)
            r = subprocess.run(["tclsh", str(p), d, str(HERE / "prd_autofo.tcl")], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return dict(l.split(" ", 1) for l in r.stdout.splitlines() if l[:1] == "R")

    def test_only_violator_nets_above_limit_get_the_cap(self):
        r = self.run_tcl()
        # big (40 loads, violator) selected; small (5) and quiet (no violator) guarded; frozen keeps its own guard
        self.assertEqual(r["R1"], "1 {32 0 1 1 1} fo=1e6 dt=0001")
        self.assertEqual(r["R2"], "0 0")                     # violators only on a low-fanout net: untouched
        self.assertEqual(r["R3"], "0 0")                     # 0 = off

    def test_restore_on_error_and_bad_value(self):
        r = self.run_tcl()
        self.assertEqual(r["R4"], "1 native repair failure fo=1e6 dt=0001")
        self.assertEqual(r["R5"], "1")

    def test_wired_into_hook_mk_run_and_eco_loop(self):
        hook = (HERE / "prd_hook.tcl").read_text()
        i, j = hook.index("ot_prd_auto_fanout $_drv_args"), hook.index("source [file join $_here prd_targeted.tcl]")
        self.assertLess(i, j)                                # before the targeted / plain repair
        self.assertIn("$::env(OT_MAX_FANOUT) == 0 && $_tfo == 0", hook)   # explicit caps win
        self.assertIn("prd_autofo.tcl", (HERE / "prd_mk.sh").read_text())
        self.assertIn("-e OT_PRD_AUTO_FANOUT=", (HERE / "prd_run.sh").read_text())
        self.assertIn("post_route_drv/prd_autofo.tcl", (HERE.parent / "eco_loop.py").read_text())

    def test_mk_rejects_bad_value(self):
        t = (HERE / "prd_mk.sh").read_text()
        self.assertIn('OT_PRD_AUTO_FANOUT=$OT_PRD_AUTO_FANOUT: want an integer', t)


if __name__ == "__main__":
    unittest.main()
