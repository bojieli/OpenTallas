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


    def test_no_wall_along_a_core_edge(self):
        # FABLE-PD-KV-HG1 B-1 / HEAD NF14: four 2.16-um sites in the 2.16-um channel above a core must not become one
        # 214-um M1-M7 strip in front of the core's edge pins; the cap gives way and the fine rects stay
        core = (0.0, 0.0, 300.0, 100.0)
        rs = [(x, 102.16, x + 2.16, 103.24) for x in (10.0, 80.0, 150.0, 222.0)]
        out, st = C.merge_rects(rs, 1, blockers=[core])
        self.assertEqual(out, sorted(rs))
        self.assertEqual((st["over_cap"], st["walls"]), (3, 0))
        old, st_old = C.merge_rects(rs, 1, blockers=[core], edge_gap_um=0)      # the old merge, for the record
        self.assertEqual(len(old), 1)
        self.assertEqual(st_old["walls"], 1)

    def test_short_merge_near_a_core_and_long_merge_far_from_it_still_happen(self):
        core = (0.0, 0.0, 300.0, 100.0)
        near = [(10.0, 102.16, 12.16, 103.24), (14.0, 102.16, 16.16, 103.24)]          # bbox 6.16 um long: no wall
        far = [(10.0, 150.0, 12.16, 151.08), (80.0, 150.0, 82.16, 151.08)]             # 50 um from the core
        out, st = C.merge_rects(near + far, 2, blockers=[core])
        self.assertEqual(out, [(10.0, 102.16, 16.16, 103.24), (10.0, 150.0, 82.16, 151.08)])
        self.assertEqual(st["walls"], 0)

    def test_bucket_prepass_keeps_the_rule(self):
        core = (0.0, 0.0, 4000.0, 100.0)
        rs = [(i * 2.5, 102.16, i * 2.5 + 2.16, 103.24) for i in range(1600)]
        out, st = C.merge_rects(rs, 100, blockers=[core])
        self.assertEqual(st["walls"], 0)
        self.assertTrue(all(o[2] - o[0] <= C.EDGE_MAX_LEN_UM for o in out))


if __name__ == "__main__":
    unittest.main()
