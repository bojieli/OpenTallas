#!/usr/bin/env python3
"""QC-SU-PROG-L2 unit tests: pin-column clearance check on EVERY leg (ht_l2.leg_clearance) + the clearance maze."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ht_l2 as H  # noqa: E402

MAC = [[90.72, 30.24, 263.544, 71.304], [90.72, 86.4, 263.544, 127.464]]          # prog_m0 SRAMs 0/1 (um)
COL = [[263.544, 25.92, 278.664, 75.624], [263.544, 82.08, 278.664, 131.784]]     # their E clock-pin columns (+-4.32)
CLR = 4.32


class Clearance(unittest.TestCase):
    def test_vertical_leg_hugging_column_fails(self):
        b = H.leg_clearance([(280.8, 40.0), (280.8, 60.0)], COL, MAC, CLR)        # 2.1 um E of the column
        self.assertTrue(b and all(k == "pin_column_clearance" for k, *_ in b))

    def test_vertical_leg_at_283_passes(self):
        self.assertEqual(H.leg_clearance([(283.1, 30.0), (283.1, 125.0)], COL, MAC, CLR), [])

    def test_leg_inside_column_fails(self):
        self.assertTrue(H.leg_clearance([(270.0, 40.0), (270.0, 41.0)], COL, MAC, CLR))

    def test_west_side_band_also_checked(self):           # clearance applies on both sides of the column
        self.assertTrue(H.leg_clearance([(261.0, 50.0), (261.0, 55.0)], COL, MAC, 4.32))

    def test_gap_row_crossing_passes(self):                # horizontal leg in the y~79 gap, outside both columns' y range
        self.assertEqual(H.leg_clearance([(250.0, 78.84), (300.0, 78.84)], COL, MAC, CLR), [])

    def test_leg_across_sram_fails(self):
        b = H.leg_clearance([(150.0, 20.0), (150.0, 80.0)], COL, MAC, CLR)
        self.assertTrue(any(k == "across_sram" for k, *_ in b))

    def test_l1_lpath_convention_is_checked(self):         # an L1 L-path whose vertical part hugs the column must fail
        p = H.lpath((280.0, 135.0), (300.0, 50.0))
        self.assertEqual(p[1], (280.0, 50.0))
        self.assertTrue(H.leg_clearance(p, COL, MAC, CLR))

    def test_maze_paths_keep_clearance(self):              # every planned maze leg clears the band by construction
        M = H.Maze([4.32, 4.32, 349.92, 140.0], MAC, COL, CLR)
        for a, b in (((285.0, 20.0), (285.0, 120.0)), ((240.0, 78.84), (300.0, 110.0)), ((60.0, 20.0), (300.0, 100.0))):
            ca, cb = M.legal_node(a), M.legal_node(b)
            pth = H.simplify([M.xy(c) for c in M.path(ca, cb)])
            self.assertEqual(H.leg_clearance(pth, COL, MAC, CLR - 1e-6), [], (a, b))

    def test_legal_node_leaves_band(self):                 # a B / leaf site at x 279.18 (old plan) is re-sited >= CLR off
        M = H.Maze([4.32, 4.32, 349.92, 140.0], MAC, COL, CLR)
        x, y = M.xy(M.legal_node((279.18, 49.14)))
        self.assertGreaterEqual(x, 278.664 + CLR)


if __name__ == "__main__":
    unittest.main(verbosity=2)
