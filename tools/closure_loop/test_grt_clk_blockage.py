"""DIE-QC-97 11-09 (QC qfd_qc_su_lane_w_l2 5_1_grt DPL-0033, "Placed in rows check failed (1)" on a DFF, four times with
the DIE-QC-58B legalization retry): the GRT repair resized a FIRM clock sink in place so its box crossed a hard placement
blockage (a macro halo) that sits over a row segment.  The off-row test passes because the row runs under the blockage,
but detailed_placement treats blocked sites as no row and cannot move a FIRM cell.  A locked instance whose box overlaps
a hard placement blockage stays PLACED; one that only touches the blockage edge, or overlaps a soft blockage, stays
FIRM; OT_GRT_CLK_LOCK_BLK=0 restores the old rule."""
import shutil
import unittest

import test_grt_clk_lock as T

# one hard blockage x 45..55 y 0..1 and one soft blockage x 20..30 (over ff1)
BLK = r"""
proc mkblk {n x0 y0 x1 y1 soft} {
  proc ::blb_$n {m} [string map [list @X0@ $x0 @Y0@ $y0 @X1@ $x1 @Y1@ $y1] { switch $m { xMin { return @X0@ } yMin { return @Y0@ } xMax { return @X1@ } yMax { return @Y1@ } } }]
  proc ::blk_$n {m} [string map [list @N@ $n @S@ $soft] { switch $m { getBBox { return ::blb_@N@ } isSoft { return @S@ } } }]
  return ::blk_$n
}
set ::blklist [list [mkblk h 45 0 55 1 0] [mkblk s 20 0 30 1 1]]
rename ::mockblock ::mockblock_base0
proc ::mockblock {m} { if {$m eq "getBlockages"} { return $::blklist }; return [::mockblock_base0 $m] }
"""


@unittest.skipUnless(shutil.which("tclsh"), "tclsh missing")
class BlockageTests(unittest.TestCase):
    def test_sink_resized_into_hard_blockage_left_placed(self):
        """ff2 at 40..50 crosses the hard blockage 45..55: PLACED for legalization, the rest stays as before."""
        log, o = T.run("4_cts.sdc", extra=BLK)
        self.assertIn("{ff2 PLACED}", o["DURING"])
        self.assertIn("{ck_buf FIRM}", o["DURING"])
        self.assertIn("OT_GRT_CLK_LOCK: 1 clock-net instances on a placement blockage left PLACED", log)
        self.assertEqual(o["AFTER"], T.AFTER)

    def test_soft_blockage_and_edge_touch_keep_the_lock(self):
        """ff1 sits on a soft blockage, ff2 ends exactly at the hard blockage edge (x1 = 45): both stay FIRM."""
        log, o = T.run("4_cts.sdc", extra=BLK + "array set ::bb {ff2 {35 0 45 1}}\n")
        self.assertIn("{ff1 FIRM}", o["DURING"])
        self.assertIn("{ff2 FIRM}", o["DURING"])
        self.assertNotIn("placement blockage", log)

    def test_opt_out(self):
        log, o = T.run("4_cts.sdc", env={"OT_GRT_CLK_LOCK_BLK": "0"}, extra=BLK)
        self.assertIn("{ff2 FIRM}", o["DURING"])
        self.assertNotIn("placement blockage", log)

    def test_no_blockages_unchanged(self):
        log, o = T.run("4_cts.sdc")
        self.assertEqual(o["DURING"], "{ck_buf FIRM} {data1 PLACED} {ff1 FIRM} {ff2 FIRM} {hb1 PLACED} {locked_buf LOCKED}")
        self.assertNotIn("placement blockage", log)


if __name__ == "__main__":
    unittest.main()
