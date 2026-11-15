import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_reserve as C


class T(unittest.TestCase):
    def test_overlap_merge(self):
        out, st = C.merge_rects([(0, 0, 2, 1), (1.5, 0, 4, 1), (10, 10, 11, 11)], 2)
        self.assertEqual(out, [(0, 0, 4, 1), (10, 10, 11, 11)])

    def test_cap_by_buckets(self):
        rs = [(i * 3.0, j * 3.0, i * 3.0 + 1.6, j * 3.0 + 0.27) for i in range(40) for j in range(40)]
        out, st = C.merge_rects(rs, 100)
        self.assertLessEqual(len(out), 100)
        self.assertEqual(st["rects_in"], 1600)
        for r in rs:                      # every input stays covered
            self.assertTrue(any(o[0] <= r[0] and o[1] <= r[1] and o[2] >= r[2] and o[3] >= r[3] for o in out))

    def test_blocker_never_covered(self):
        core = (4.0, 0.0, 6.0, 1.0)
        rs = [(0, 0, 1, 1), (8, 0, 9, 1)]
        out, _ = C.merge_rects(rs, 1, blockers=[core])
        self.assertEqual(len(out), 2)
        for o in out:
            self.assertFalse(C._hits(o, [core]))

    def test_waste_budget_stops_merge(self):
        rs = [(0, 0, 1, 1), (50, 50, 51, 51)]
        out, st = C.merge_rects(rs, 1, max_waste_um2=10.0)
        self.assertEqual(len(out), 2)
        self.assertEqual(st["over_cap"], 1)

    def test_deterministic(self):
        rs = [(i * 1.0, 0, i * 1.0 + 0.5, 0.27) for i in range(50)]
        self.assertEqual(C.merge_rects(rs, 5), C.merge_rects(list(reversed(rs)), 5))


if __name__ == "__main__":
    unittest.main()
