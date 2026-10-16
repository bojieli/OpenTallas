"""GRT183-RESUME (tools/run_abi3_physical.py + physical/common_flow/grt183_resume.tcl): local, no Docker/OpenROAD."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import run_abi3_physical as R  # noqa: E402

HOOK = ROOT / "physical/common_flow/grt183_resume.tcl"


class ConfigHook(unittest.TestCase):
    def test_chains_block_hook_after_resume_hook(self):
        with tempfile.TemporaryDirectory() as td:
            case = Path(td)
            cfg = R.apply_grt183_hook(["export A = 1", "export PRE_GLOBAL_ROUTE_TCL = /work/hooks/pre_grt.tcl"], case)
            self.assertEqual(cfg, ["export A = 1", "export PRE_GLOBAL_ROUTE_TCL = /work/hooks/pre_grt_ot_grt183.tcl"])
            body = (case / "hooks/pre_grt_ot_grt183.tcl").read_text().splitlines()
            self.assertEqual(body[1:], ["source /work/hooks/ot_grt183_resume.tcl", "source /work/hooks/pre_grt.tcl"])
            self.assertEqual((case / "hooks/ot_grt183_resume.tcl").read_bytes(), HOOK.read_bytes())
            self.assertEqual(R.apply_grt183_hook(list(cfg), case), cfg)      # idempotent: no self-chaining

    def test_opt_out_keeps_config(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = ["export PRE_GLOBAL_ROUTE_TCL = x"]
            import os
            os.environ["OT_GRT183_RESUME"] = "0"
            try:
                self.assertEqual(R.apply_grt183_hook(list(cfg), Path(td)), cfg)
            finally:
                del os.environ["OT_GRT183_RESUME"]


class Prepare(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.case = Path(self.td.name)
        self.r = self.case / "results/asap7/n/base"; self.l = self.case / "logs/asap7/n/base"
        self.r.mkdir(parents=True); self.l.mkdir(parents=True)
        (self.r / "4_cts.odb").write_bytes(b"cts")
        (self.case / "orfs_flow.log").write_text("attempt1")

    def tearDown(self):
        self.td.cleanup()

    def test_no_marker_no_resume(self):
        (self.l / "5_1_grt.log").write_text("[ERROR GRT-0183] Net x\n")
        (self.r / "5_1_grt.grt183_resume.odb").write_bytes(b"resized")
        self.assertIsNone(R.grt183_resume_prepare(self.r, self.l, self.case, "orfs_flow.log"))
        self.assertEqual((self.r / "4_cts.odb").read_bytes(), b"cts")

    def test_resume_once_then_restore(self):
        (self.l / "5_1_grt.log").write_text("[ERROR GRT-0183] Net _04241_ ...\nOT_GRT183_RESUME_SAVED helper=repair_design_helper\n")
        (self.r / "5_1_grt.grt183_resume.odb").write_bytes(b"resized")
        rec = R.grt183_resume_prepare(self.r, self.l, self.case, "orfs_flow.log")
        self.assertEqual(rec["schema"], "opentallas.grt183_resume.v1")
        self.assertEqual((self.r / "4_cts.odb").read_bytes(), b"resized")
        self.assertTrue((self.l / "5_1_grt.grt183_attempt1.log").is_file())
        self.assertTrue((self.case / "orfs_flow.log.grt183_attempt1").is_file())
        self.assertEqual(json.loads((self.r / "5_1_grt.grt183_recovered.json").read_text())["resume_odb_sha256"],
                         rec["resume_odb_sha256"])
        # a second GRT-0183 after the resume is never resumed again
        self.assertIsNone(R.grt183_resume_prepare(self.r, self.l, self.case, "orfs_flow.log"))
        R.grt183_resume_restore(self.r)
        self.assertEqual((self.r / "4_cts.odb").read_bytes(), b"cts")
        self.assertFalse((self.r / "4_cts.pre_grt183.odb").exists())


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
  if {[string is integer -strict $c]} {      ;# obstruction handle i
    if {[lindex $args 1] eq "getBBox"} { return "bx$c" }
  }
  if {[string match bx* $c]} {
    set r [lindex $::obs [string range $c 2 end]]
    switch [lindex $args 1] { getTechLayer { return "ly[lindex $r 0]" } xMin { return [lindex $r 1] } yMin { return [lindex $r 2] }
                              xMax { return [lindex $r 3] } yMax { return [lindex $r 4] } }
  }
  if {[string match ly* $c] && [lindex $args 1] eq "getName"} { return [string range $c 2 end] }
  uplevel 1 [list _unknown {*}$args]
}
proc write_db {f} { set h [open $f w]; puts $h $::obs; close $h }
proc repair_design_helper {} { error GRT-0183 }
proc repair_timing_helper {args} { return ok }
source [lindex $argv 1]
lappend ::obs {M5 40 0 50 10}   ;# the block's PRE hook adds a guard after the resume hook recorded the start state
if {[catch {repair_design_helper} m]} { puts "ERR $m" }
puts "TIMING [repair_timing_helper 1]"
puts "DESTROYED $::dbs"
'''


class TclHook(unittest.TestCase):
    def test_saves_resume_without_hook_shapes_and_reraises(self):
        with tempfile.TemporaryDirectory() as td:
            p = subprocess.run(["tclsh", "/dev/stdin", td, str(HOOK)], input=STUB, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("OT_GRT183_RESUME_SAVED helper=repair_design_helper", p.stdout)
            self.assertIn("hook_shapes_dropped=1", p.stdout)
            self.assertIn("ERR GRT-0183", p.stdout)
            self.assertIn("TIMING ok", p.stdout)
            self.assertIn("DESTROYED 2", p.stdout)
            saved = (Path(td) / "5_1_grt.grt183_resume.odb").read_text()
            self.assertIn("20 0 30 10", saved)
            self.assertNotIn("40 0 50 10", saved)

    def test_refuses_second_resume(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "5_1_grt.grt183_recovered.json").write_text("{}")
            p = subprocess.run(["tclsh", "/dev/stdin", td, str(HOOK)], input=STUB, text=True, capture_output=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("OT_GRT183_RESUME_REFUSED", p.stdout)
            self.assertFalse((Path(td) / "5_1_grt.grt183_resume.odb").exists())


if __name__ == "__main__":
    unittest.main()
