"""KW6-CLASS 11-04 (S81 t34/t66 DPL-0033 "Placed in rows check failed"): sites in the row-cut halo around a macro are
occupied for FIRM landing cells.  Runs the REAL cland_occupy / cland_occupy_row_gaps / cland_put procs (OpenDB mocked)."""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

TCL = Path(__file__).with_name("landing_placement.tcl").read_text()


def procs():
    out = ""
    for head in (r"proc cland_occupy \{x y w h\} \{", r"proc cland_occupy_row_gaps \{rows\} \{",
                 r"proc cland_put \{i rect tag \{sp \{\}\} \{cur 0\}\} \{"):
        out += re.search(head + r"\n.*?\n\}\n", TCL, re.S).group(0)
    return out


# core 40 x 10.8 um, site 54, row 270.  Row y=0 whole; y=270 cut: [0,10000) and [20000,40000)
MOCK = r"""
set ff_x0 0; set ff_y0 0; set ff_x1 40000; set ff_y1 10800; set ff_rh 270; set ff_sw 54; set ff_dbu 1000
set ff_orient [dict create 0 R0 270 MX]
set cland_done {}; set cland_n 0; set cland_cursor {}; set cland_fh [open /dev/null w]; set cland_occ [dict create]
proc mkrow {n x0 y0 x1 y1} {
 proc $n {op} [list return b$n]
 proc b$n {op} [format {switch $op { xMin {return %d} yMin {return %d} xMax {return %d} yMax {return %d} }} $x0 $y0 $x1 $y1]
}
mkrow r0 0 0 40000 270; mkrow r1 0 270 10000 540; mkrow r2 20000 270 40000 540
set rows {r0 r1 r2}
cland_occupy_row_gaps $rows
puts "OCC0 [expr {[dict exists $cland_occ 0] ? [dict get $cland_occ 0] : {}}]"
puts "OCC1 [dict get $cland_occ 1]"
set ::loc {}
proc m0 {op args} { switch $op { getWidth { return 108 } getHeight { return 270 } isBlock { return 0 } getName { return DFFx1 } } }
proc c0 {op args} { switch $op { getName { return u_cland_ft0_i/q } getMaster { return m0 }
  getPlacementStatus { return PLACED } setLocation { set ::loc $args } default {} } }
if {[catch {cland_put c0 {12.0 0.27 18.0 0.54} ring:x 1.0} e]} { puts "ERR $e" } else { puts "LOC $::loc" }
"""


@unittest.skipIf(shutil.which("tclsh") is None, "tclsh not installed")
class RowGaps(unittest.TestCase):
    def run_tcl(self):
        r = subprocess.run(["tclsh"], input=procs() + MOCK, capture_output=True, text=True)
        self.assertEqual((r.returncode, r.stderr), (0, ""))
        return r.stdout

    def test_only_the_cut_is_occupied(self):
        out = self.run_tcl()
        self.assertIn("OCC0 \n", out)
        self.assertIn("OCC1 {10000 20000}", out)

    def test_cell_gets_no_site_in_the_cut(self):
        self.assertIn("ERR OT_CLAND no legal", self.run_tcl())


class Order(unittest.TestCase):
    def test_runs_before_ring_placement(self):
        self.assertLess(TCL.index("cland_occupy_row_gaps [$ff_blk getRows]"), TCL.index("foreach spec $cland_groups"))


if __name__ == "__main__":
    unittest.main()
