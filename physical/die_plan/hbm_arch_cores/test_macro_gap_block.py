"""DIE-HBM-82-EP6: macro_gap_blockages keeps out no-pin gaps only (vms_bank_q0 vecd4ae class fix)."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gen_core_kit_hbm as G

W, H = 174744, 70488
EW = [("M4", 0, 1000, 200, 1048), ("M4", W - 200, 1000, W, 1048)]          # pins on W + E edges only


def pins(m):
    return W, H, EW


class T(unittest.TestCase):
    def test_vms_bank_gap(self):
        pl = [dict(macro="m", xy_um=[47.616, y], orient="R0") for y in (76.38, 164.172, 234.732)]
        self.assertEqual(G.macro_gap_blockages(pl, pins, 4.32), [(43.296, 146.868, 226.68, 164.172)])

    def test_pin_edge_gap_kept(self):
        pl = [dict(macro="m", xy_um=[x, 10.0], orient="R0") for x in (10.0, 10.0 + 174.744 + 14.04)]
        self.assertEqual(G.macro_gap_blockages(pl, pins, 4.32), [])

    def test_wide_gap_kept(self):
        pl = [dict(macro="m", xy_um=[10.0, y], orient="R0") for y in (10.0, 10.0 + 70.488 + 40.0)]
        self.assertEqual(G.macro_gap_blockages(pl, pins, 4.32), [])


if __name__ == "__main__":
    unittest.main()
