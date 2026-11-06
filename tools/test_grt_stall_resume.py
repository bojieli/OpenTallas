"""KW-FIX-17 11-05 GRT-STALL-RESUME hook (physical/common_flow/grt_stall_resume.tcl): local tclsh, no OpenROAD.
    python3 -m pytest -q tools/test_grt_stall_resume.py"""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HOOK = ROOT / "physical/common_flow/grt_stall_resume.tcl"
G183 = ROOT / "physical/common_flow/grt183_resume.tcl"

STUB = r'''
set ::env(RESULTS_DIR) [lindex $argv 0]
set ::obs {{M5 0 0 10 10} {M5 20 0 30 10}}
set ::dbs {}
namespace eval odb { proc dbObstruction_destroy {o} { set ::obs [lreplace $::obs $o $o {}]; lappend ::dbs $o } }
namespace eval ord { proc get_db_block {} { return blk } }
proc blk {m} { if {$m eq "getObstructions"} { set out {}; set i 0
    foreach o $::obs { if {$o ne {}} { lappend out $i }; incr i }; return $out } else { return {} } }
rename unknown _unknown
proc unknown {args} {
  set c [lindex $args 0]
  if {[string is integer -strict $c]} { if {[lindex $args 1] eq "getBBox"} { return "bx$c" } }
  if {[string match bx* $c]} {
    set r [lindex $::obs [string range $c 2 end]]
    switch [lindex $args 1] { getTechLayer { return "ly[lindex $r 0]" } xMin { return [lindex $r 1] } yMin { return [lindex $r 2] }
                              xMax { return [lindex $r 3] } yMax { return [lindex $r 4] } }
  }
  if {[string match ly* $c] && [lindex $args 1] eq "getName"} { return [string range $c 2 end] }
  uplevel 1 [list _unknown {*}$args]
}
proc write_db {f} { set h [open $f w]; puts $h $::obs; close $h }
proc repair_design_helper {} { return @RD@ }
source [lindex $argv 1]
source [lindex $argv 2]
lappend ::obs {M5 40 0 50 10}   ;# the kit's PRE hook adds a guard after both hooks recorded the start state
if {[catch {repair_design_helper} m]} { puts "ERR $m" } else { puts "RD $m" }
puts "DESTROYED $::dbs"
puts "OBS $::obs"
'''


def run(td, rd="done", env=None):
    stub = STUB.replace("return @RD@", "return done" if rd == "done" else "error GRT-0183")
    return subprocess.run(["tclsh", "/dev/stdin", td, str(HOOK), str(G183)], input=stub, text=True, capture_output=True,
                          env=dict(os.environ, **(env or {})))


class StallHook(unittest.TestCase):
    def test_saves_after_repair_design_without_touching_live_design(self):
        with tempfile.TemporaryDirectory() as td:
            p = run(td)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("RD done", p.stdout)
            self.assertIn("OT_GRT_STALL_SAVED", p.stdout)
            self.assertIn("hook_shapes=1", p.stdout)
            self.assertIn("DESTROYED \n", p.stdout)
            self.assertIn("40 0 50 10", (Path(td) / "5_1_grt.stall_resume.odb").read_text())
            self.assertEqual((Path(td) / "5_1_grt.stall_resume.shapes").read_text().strip(), "{O M5 40 0 50 10}")

    def test_no_save_on_failure_after_resume_or_opt_out(self):
        with tempfile.TemporaryDirectory() as td:
            p = run(td, rd="fail")
            self.assertIn("ERR GRT-0183", p.stdout)
            self.assertIn("OT_GRT183_RESUME_SAVED", p.stdout)        # the GRT-0183 resume is unchanged
            self.assertNotIn("OT_GRT_STALL_SAVED", p.stdout)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "5_1_grt.grt183_recovered.json").write_text("{}")
            self.assertNotIn("OT_GRT_STALL_SAVED", run(td).stdout)
        with tempfile.TemporaryDirectory() as td:
            p = run(td, env={"OT_GRT_STALL_RESUME": "0"})
            self.assertNotIn("OT_GRT_STALL_SAVED", p.stdout)
            self.assertFalse((Path(td) / "5_1_grt.stall_resume.odb").exists())

    def test_resume_drops_listed_shapes_before_start_state(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "5_1_grt.stall_strip.shapes").write_text("{O M5 20 0 30 10}\n")
            (Path(td) / "5_1_grt.grt183_recovered.json").write_text("{}")
            p = run(td)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("OT_GRT_STALL_RESUMED hook_shapes_dropped=1 of 1", p.stdout)
            self.assertIn("DESTROYED 1", p.stdout)
            self.assertIn("OBS {M5 0 0 10 10} {} {M5 40 0 50 10}", p.stdout)


if __name__ == "__main__":
    unittest.main()
