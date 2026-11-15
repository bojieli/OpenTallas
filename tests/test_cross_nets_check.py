"""CB-CROSS preflight geometry (tools/die_plan/cross_nets_check.py), no OpenROAD needed."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools/die_plan"))
import cross_nets_check as C

TILE = (100.0, 0.0, 560.0, 1160.0)


class Cross(unittest.TestCase):
    def test_straddle(self):
        self.assertTrue(C.straddles(TILE, [90, 570], [500, 520]))          # both sides, level with the tile
        self.assertFalse(C.straddles(TILE, [90, 300], [500, 520]))         # ends inside / one side only
        self.assertFalse(C.straddles(TILE, [90, 570], [500, 1200]))        # one end above the tile: goes round
        self.assertFalse(C.straddles(TILE, [90, 120], [500, 520]))

    def test_count_split(self):
        nets = [("u_d3_x.r[0]", [90, 570], [10, 20]), ("PORT", [90, 570], [10, 20]),
                ("u_cland_nb_i00/_1_", [90, 570], [10, 20]), ("a", [10, 20], [10, 20])]
        self.assertEqual(C.count({"u_t11": TILE}, nets), {"u_t11": [2, 1]})

    def test_single_pin_ignored(self):
        self.assertEqual(C.count({"t": TILE}, [("a", [90], [10])]), {})


if __name__ == "__main__":
    unittest.main()
