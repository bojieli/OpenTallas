"""C-REPAIR-BUF-OVER-MACRO (KV-INT-R3/FIRM 11-27): repair_macro_clear.tcl is placement only, gen_phys sources it from the PRE_DETAIL_PLACE
hook only for plan types that opt in ("repair_macro_clear": true), and dpl_repair_disp_check keys on the DPL displacement."""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dpl_repair_disp_check as C  # noqa: E402
import gen_phys as GP  # noqa: E402

TCL = HERE.parents[1] / "physical/common_flow/repair_macro_clear.tcl"
LOG_BAD = "OT_CLAND released 0 FIRM cland cells grown into an occupied site\nPlacement Analysis\n---\ntotal displacement 1.0 u\naverage displacement 0.7 u\nmax displacement          255.5 u\n"
LOG_GOOD = "OT_REPAIR_MACRO_CLEAR rects=353 cells=6365 moved=6238 unresolved=127 max_move_um=194.6\nPlacement Analysis\nmax displacement          31.0 u\n"


class RepairMacroClearKit(unittest.TestCase):
    def test_line_sources_kit_copy(self):
        self.assertIn("source /work/repair_macro_clear.tcl", GP.REPAIR_MACRO_CLEAR_LINE)

    def test_generator_gated_and_copies(self):
        src = (HERE / "gen_phys.py").read_text()
        self.assertIn('if t.get("repair_macro_clear", False) is True:', src)
        self.assertIn('kd / "repair_macro_clear.tcl"', src)

    def test_schema_key(self):
        self.assertIn('"repair_macro_clear": {"type": "boolean"}', (HERE / "schema.py").read_text())

    def test_tcl_placement_only(self):
        body = "\n".join(l for l in TCL.read_text().splitlines() if not l.lstrip().startswith("#"))
        for forbidden in ("insert_buffer", "repair_design", "repair_timing", "makeInst", "dbInst_create", "connect", "disconnect",
                          "set_dont_touch", "setPlacementStatus"):
            self.assertNotIn(forbidden, body)
        self.assertIn("setLocation", body)
        self.assertIn("isSoft", body)                      # soft blockages are not clearance
        self.assertIn('ne "PLACED"', body)                 # FIRM / LOCKED / FIXED cells never move

    def test_tcl_v2_union_exit_and_tiny_blockage_skip(self):
        body = "\n".join(l for l in TCL.read_text().splitlines() if not l.lstrip().startswith("#"))
        self.assertIn("OT_RMC_MIN_BLOCKAGE_UM", body)      # tiny hard blockages are not macro-sized rectangles
        self.assertIn("for {set it 0} {$it < 64} {incr it}", body)   # exit walks through abutting rectangles
        self.assertIn("switch $dir", body)

    def test_check_flags_displacement_not_firm_release(self):
        v, mx, mc, rel = C.check(LOG_BAD)
        self.assertEqual((v, mx, mc, rel), ("FAIL", 255.5, "off", 0))      # FIRM released = 0 and still FAIL
        v, mx, mc, rel = C.check(LOG_GOOD)
        self.assertEqual((v, mx), ("PASS", 31.0))
        self.assertTrue(mc.startswith("rects=353"))
        self.assertEqual(C.check("nothing")[0], "NODATA")

    def test_check_limit(self):
        self.assertEqual(C.check(LOG_GOOD, 20.0)[0], "FAIL")


if __name__ == "__main__":
    unittest.main()
