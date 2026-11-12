"""MGB-CLOCK-KEEP (VISLAYOUT2-HBM 11-11, COORD adopted): the macro-gap row cut keeps the rows under the plan clock
entry (+ root-buffer room) and reports whether that gap is open at both ends.  Case = hnx_vms_bank_q0_faces__vecd4ae
(plan_r2_restore core_macros: u_a/u_b/u_c 1r1w_1024x256 at x 47.616, y 76.38 / 164.172 / 234.732; 8 clk ports at the
clock entry (133.608..134.28, 155.52); outline 270 x 403.92)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G

W, H = 174744, 70488
EW = [("M4", 0, 1000, 200, 1048), ("M4", W - 200, 1000, W, 1048)]          # pins on W + E edges only
OW, OH = 270.0, 403.92


def pins(m):
    return W, H, EW


VMS = [dict(macro="m", xy_um=[47.616, y], orient="R0") for y in (76.38, 164.172, 234.732)]
CLKS = ["clk", "clk_e", "clk_w", "clk_n", "clk_s", "clk_macro0", "clk_macro1", "clk_macro2"]
CPINS = [dict(name=n, x=133.608 + 0.096 * i, y=155.52) for i, n in enumerate(CLKS)] + [dict(name="d0", x=0.0, y=20.0)]


def boxes(pl):
    return [(p["xy_um"][0], p["xy_um"][1], p["xy_um"][0] + W / 1000.0, p["xy_um"][1] + H / 1000.0) for p in pl]


class T(unittest.TestCase):
    def test_keep_window_from_interior_clock_pins(self):
        k = G.clock_keep_windows(CPINS, CLKS, OW, OH)
        self.assertEqual(k, [(124.968, 146.88, 142.92, 164.16)])

    def test_face_clock_pins_give_no_window(self):
        face = [dict(name="clk", x=0.0, y=155.52)]
        self.assertEqual(G.clock_keep_windows(face, ["clk"], OW, OH), [])

    def test_vms_gap_cut_split_around_clock_entry(self):
        k = G.clock_keep_windows(CPINS, CLKS, OW, OH)
        self.assertEqual(G.macro_gap_blockages(VMS, pins, 4.32, keep=k),
                         [(43.296, 146.868, 124.968, 164.172), (142.92, 146.868, 226.68, 164.172)])

    def test_no_keep_is_ep6(self):
        self.assertEqual(G.macro_gap_blockages(VMS, pins, 4.32, keep=()),
                         G.macro_gap_blockages(VMS, pins, 4.32))

    def test_side_by_side_gap_split_in_y(self):
        NS = [("M4", 1000, 0, 1048, 200), ("M4", 1000, H - 200, 1048, H)]   # pins on S + N edges only
        pl = [dict(macro="m", xy_um=[x, 10.0], orient="R0") for x in (10.0, 10.0 + 174.744 + 17.3)]
        gx0 = 10.0 + 174.744
        k = [(gx0, 40.0, gx0 + 17.3, 50.0)]
        got = G.macro_gap_blockages(pl, lambda m: (W, H, NS), 4.32, keep=k)
        self.assertEqual(got, [(184.744, 5.68, 202.044, 40.0), (184.744, 50.0, 202.044, 84.808)])

    def test_vms_gap_is_open_at_both_ends(self):
        k = G.clock_keep_windows(CPINS, CLKS, OW, OH)[0]
        e = G.clock_gap_ends(boxes(VMS), k, OW, OH)
        self.assertEqual((e["axis"], e["gap_um"], e["open"]), ("x", 17.304, True))
        self.assertAlmostEqual(e["ends"]["W"], 47.616, places=3)

    def test_dead_end_gap_flagged(self):
        # E end closed by a third macro 4.3 um past the pair (ot_wbq_root_g1 class)
        pl = boxes(VMS[:2]) + [(222.36 + 4.3, 100.0, 265.0, 200.0)]
        k = G.clock_keep_windows(CPINS, CLKS, OW, OH)[0]
        e = G.clock_gap_ends(pl, k, OW, OH)
        self.assertFalse(e["open"])
        self.assertAlmostEqual(e["ends"]["E"], 4.3, places=3)

    def test_window_not_in_gap(self):
        self.assertIsNone(G.clock_gap_ends(boxes(VMS), (10.0, 10.0, 20.0, 20.0), OW, OH))


if __name__ == "__main__":
    unittest.main()
