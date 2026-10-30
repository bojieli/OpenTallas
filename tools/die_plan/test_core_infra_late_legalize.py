"""ot_ci_late_legalize fails closed on an illegal late DPL (DIE-S81-36 10-30); pure Tcl stubs, no OpenROAD."""
import pathlib
import shutil
import subprocess
import unittest

SOURCE = pathlib.Path(__file__).with_name("core_infra_late.tcl")

HARNESS = r'''
proc clock_tree_synthesis {args} {}
source SOURCE
set ::ot_ci_u 1000
set ::log {}
proc bbox {method} {switch $method {xMin {return 9000} yMin {return 9000} xMax {return 11000} yMax {return 11000}}}
proc inst {name method args} {
  switch $method {
    getPlacementStatus {return [dict get $::status $name]}
    setPlacementStatus {lappend ::log "$name=[lindex $args 0]"; dict set ::status $name [lindex $args 0]}
    getBBox {return bbox}
    getName {return $name}
  }
}
foreach n {late other} {interp alias {} $n {} inst $n}
set ::status [dict create late PLACED other PLACED]
proc blk {method} {return {late other}}
set ::ot_ci_b blk
set ::ot_ci_late_cells [list [list late 10.0 10.0 {0 0 20 20}]]
proc detailed_placement {args} {lappend ::log dpl}
proc check_placement {args} {lappend ::log check; if {$::illegal} {error "DPL-0033 detailed placement checks failed"}}
set ::illegal ILLEGAL
set rc [catch {ot_ci_late_legalize 1.0} msg]
puts "RC $rc"
puts "MSG $msg"
puts "LOG $::log"
'''


@unittest.skipUnless(shutil.which("tclsh"), "tclsh not installed")
class LateLegalize(unittest.TestCase):
    def run_tcl(self, illegal):
        r = subprocess.run(["tclsh"], input=HARNESS.replace("SOURCE", str(SOURCE)).replace("ILLEGAL", str(int(illegal))),
                           capture_output=True, text=True, check=True)
        out = dict(ln.split(" ", 1) for ln in r.stdout.splitlines() if ln[:3] in ("RC ", "MSG", "LOG"))
        out["stdout"] = r.stdout
        return out

    def test_illegal_dpl_fails_closed_and_restores_held_cells(self):
        out = self.run_tcl(True)
        self.assertEqual(out["RC"], "1")
        self.assertTrue(out["MSG"].startswith("OT_CORE_INFRA_LATE_DPL_UNLEGAL DPL-0033"))
        self.assertEqual(out["LOG"], "other=FIRM dpl check other=PLACED")    # check while held, restored after

    def test_legal_dpl_unchanged(self):
        out = self.run_tcl(False)
        self.assertEqual(out["RC"], "0")
        self.assertEqual(out["LOG"], "other=FIRM dpl check other=PLACED late=FIRM")
        self.assertIn("OT_CORE_INFRA_LATE_DPL cells=1 held=1 max_disp_um=0.000", out["stdout"])


if __name__ == "__main__":
    unittest.main()
