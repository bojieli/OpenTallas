"""DIE-HBM-90 11-07 (HBM ot_hbm_su_static_qcore_r13 5_1_grt DPL-0033, "Placed in rows check failed (1):
clkleafrepg_19303" + "Padding check failed (1)"): a clock-net instance outside every row segment (off the site pitch,
on no row, or past a row end) stays PLACED under GRT-CLK-LOCK, like an overlap; on-grid instances stay FIRM; a block
without readable rows keeps the old overlap-only rule."""
import shutil
import unittest

import test_grt_clk_lock as T

# two rows y 0 and y 1, site width 10; row 0 is cut at x 75..95 (a macro), so it has two segments
ROWS = r"""
proc ::site {m} { return 10 }
proc mkrow {n x0 y x1} {
  proc ::rb_$n {m} [string map [list @X0@ $x0 @Y@ $y @X1@ $x1] { switch $m { xMin { return @X0@ } yMin { return @Y@ } xMax { return @X1@ } } }]
  proc ::row_$n {m} [string map [list @N@ $n] { switch $m { getBBox { return ::rb_@N@ } getSite { return ::site } } }]
  return ::row_$n
}
set ::rowlist [list [mkrow a 0 0 70] [mkrow b 100 0 200] [mkrow c 0 1 200]]
rename ::mockblock ::mockblock_base
proc ::mockblock {m} { if {$m eq "getRows"} { return $::rowlist }; return [::mockblock_base $m] }
"""


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class OffRowTests(unittest.TestCase):
    def test_on_grid_lock_unchanged(self):
        log, o = T.run("4_cts.sdc", extra=ROWS + "array set ::bb {locked_buf {100 0 110 1}}\n")
        self.assertEqual(o["DURING"], "{ck_buf FIRM} {data1 PLACED} {ff1 FIRM} {ff2 FIRM} {hb1 PLACED} {locked_buf LOCKED}")
        self.assertNotIn("off-row", log)

    def test_off_site_buffer_left_placed(self):
        log, o = T.run("4_cts.sdc", extra=ROWS + "array set ::bb {ck_buf {3 0 13 1} locked_buf {100 0 110 1}}\n")
        self.assertIn("{ck_buf PLACED}", o["DURING"])
        self.assertIn("{ff1 FIRM}", o["DURING"])
        self.assertIn("OT_GRT_CLK_LOCK: 1 off-row clock-net instances left PLACED", log)
        self.assertEqual(o["AFTER"], T.AFTER)

    def test_off_row_y_left_placed(self):
        log, o = T.run("4_cts.sdc", extra=ROWS + "array set ::bb {ff2 {40 7 50 8} locked_buf {100 0 110 1}}\n")
        self.assertIn("{ff2 PLACED}", o["DURING"])
        self.assertIn("{ck_buf FIRM}", o["DURING"])

    def test_past_row_end_into_cut_left_placed(self):
        """ff2 at x 60..80 on row 0 crosses the row end at 70 (cut for a macro): not inside any segment."""
        log, o = T.run("4_cts.sdc", extra=ROWS + "array set ::bb {ff2 {60 0 80 1} locked_buf {100 0 110 1}}\n")
        self.assertIn("{ff2 PLACED}", o["DURING"])
        self.assertIn("{ff1 FIRM}", o["DURING"])

    def test_no_rows_keeps_old_rule(self):
        log, o = T.run("4_cts.sdc", extra="array set ::bb {ck_buf {3 0 13 1}}\n")
        self.assertIn("{ck_buf FIRM}", o["DURING"])
        self.assertNotIn("off-row", log)


if __name__ == "__main__":
    unittest.main()
