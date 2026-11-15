import math, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_stamp as S


class T(unittest.TestCase):
    def test_box_size(self):
        b = S.cell_box((10, 10))
        self.assertAlmostEqual(b[2] - b[0], 2.70)
        self.assertAlmostEqual(b[3] - b[1], 0.81)

    def test_slide_clears_pg(self):
        r = S.cell_box((4.9, 5.0))            # over the pair [3.984, 4.656]
        out, d = S.slide_off_pg(r)
        self.assertIsNotNone(out)
        self.assertLessEqual(d, 1.3 + 1e-9)
        self.assertIsNone(S._pg_overlap(out[0], out[2]))
        r2 = S.cell_box((8.0, 5.0))           # already in the free gap
        self.assertEqual(S.slide_off_pg(r2), (r2, 0.0))

    def test_orient_is_isometry_and_involution(self):
        W, H = 717.12, 1036.8
        a, b = (10.0, 20.0, 12.7, 20.81), (300.0, 900.0, 302.7, 900.81)
        for o in ("R0", "MY", "MX", "R180"):
            ra, rb = S.orient_rect(a, (W, H), o), S.orient_rect(b, (W, H), o)
            ca = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
            cb = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
            da = ((ra[0] + ra[2]) / 2, (ra[1] + ra[3]) / 2)
            db = ((rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2)
            self.assertAlmostEqual(math.dist(ca, cb), math.dist(da, db))       # leg length preserved exactly
            self.assertAlmostEqual(ra[2] - ra[0], 2.70)                         # box mirrored, same size
            self.assertEqual(tuple(round(v, 6) for v in S.orient_rect(ra, (W, H), o)), tuple(round(v, 6) for v in a))

    def test_stamp_same_site_count(self):
        t = [(1, 1, 3.7, 1.81), (50, 60, 52.7, 60.81)]
        s = S.stamp(t, (100, 100), {"i0": "R0", "i1": "MY", "i2": "R180"})
        self.assertTrue(all(len(v) == 2 for v in s.values()))

    def test_start_stage_cap(self):
        st = [(i * 10.0, 5.0) for i in range(30)]
        self.assertLessEqual(len(S.start_stage_rows(st, cap=7)), 7)


if __name__ == "__main__":
    unittest.main()
