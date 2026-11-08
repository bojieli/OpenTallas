"""DIE-HBM-90 11-07 (HBM ot_hbm_su_static_qcore_r13 5_1_grt DPL-0033, "Placed in rows check failed (1):
clkleafrepg_19303"): a clock-net instance off the row/site grid stays PLACED under GRT-CLK-LOCK, like an overlap;
on-grid instances stay FIRM; a block without readable rows keeps the old overlap-only rule."""
import shutil
import unittest

import test_grt_clk_lock as T

ROWS = r"""
proc ::site {m} { return 10 }
proc ::row0 {m} { switch $m { getOrigin { return {0 0} } getSite { return ::site } } }
proc ::row1 {m} { switch $m { getOrigin { return {0 1} } getSite { return ::site } } }
rename ::mockblock ::mockblock_base
proc ::mockblock {m} { if {$m eq "getRows"} { return {::row0 ::row1} }; return [::mockblock_base $m] }
"""


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class OffRowTests(unittest.TestCase):
    def test_on_grid_lock_unchanged(self):
        log, o = T.run("4_cts.sdc", extra=ROWS)
        self.assertEqual(o["DURING"], "{ck_buf FIRM} {data1 PLACED} {ff1 FIRM} {ff2 FIRM} {hb1 PLACED} {locked_buf LOCKED}")
        self.assertNotIn("off-row", log)

    def test_off_site_buffer_left_placed(self):
        log, o = T.run("4_cts.sdc", extra=ROWS + "array set ::bb {ck_buf {3 0 13 1}}\n")
        self.assertIn("{ck_buf PLACED}", o["DURING"])
        self.assertIn("{ff1 FIRM}", o["DURING"])
        self.assertIn("OT_GRT_CLK_LOCK: 1 off-row clock-net instances left PLACED", log)
        self.assertEqual(o["AFTER"], T.AFTER)

    def test_off_row_y_left_placed(self):
        log, o = T.run("4_cts.sdc", extra=ROWS + "array set ::bb {ff2 {40 7 50 8}}\n")
        self.assertIn("{ff2 PLACED}", o["DURING"])
        self.assertIn("{ck_buf FIRM}", o["DURING"])

    def test_no_rows_keeps_old_rule(self):
        log, o = T.run("4_cts.sdc", extra="array set ::bb {ck_buf {3 0 13 1}}\n")
        self.assertIn("{ck_buf FIRM}", o["DURING"])
        self.assertNotIn("off-row", log)


if __name__ == "__main__":
    unittest.main()
