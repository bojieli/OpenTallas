import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import clksite_reserve as C


class T(unittest.TestCase):
    def test_uncovered_types_after_clock_rerun(self):
        # FABLE-PD-HEAD-0015 A1: a rerun moved trunk cells of types outside the fixed regenerate list
        types = {"a": {"clock": {"reserved_sites_um": [dict(rect_um=[0, 0, 10, 1], kind="die_clock_tree", route_layers="M1-M7")]}},
                 "b": {"clock": {"reserved_sites_um": [dict(rect_um=[0, 0, 10, 1], kind="die_clock_tree", route_layers="M1-M4"),
                                                      dict(rect_um=[20, 0, 30, 1], kind="die_clock_tree", route_layers="M5-M7")]}},
                 "c": {"clock": {}}}
        win = {"a": [(1, 0, 2.6, 0.27)], "b": [(1, 0, 2.6, 0.27), (21, 0, 22.6, 0.27)], "c": [(0, 0, 1, 1)]}
        # M5-M7 keepout rows do not hold a cell; a type with no die_clock_tree row is unreserved by design
        self.assertEqual(C.uncovered_types(types, win), {"b": 1})
        # a tall cell spanning two merged row rects is covered by their union
        types["d"] = {"clock": {"reserved_sites_um": [dict(rect_um=[0, 0, 3, 0.4], kind="die_clock_tree"),
                                                      dict(rect_um=[0, 0.4, 3, 0.81], kind="die_clock_tree")]}}
        self.assertEqual(C.uncovered_types(types, dict(win, d=[(1, 0, 2.6, 0.81)])), {"b": 1})
        self.assertEqual(C.uncovered_types(types, dict(win, d=[(1, 0, 3.2, 0.81)])), {"b": 1, "d": 1})
        win["a"] = [(9.5, 0, 11.1, 0.27)]
        self.assertEqual(C.uncovered_types(types, win), {"a": 1, "b": 1})

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

    def test_point_blocks_merge_without_core_edge_wall(self):
        rs = [(0, 0, 1, 1), (8, 0, 9, 1)]
        point = (4, .2, 4.5, .8)
        out, _ = C.merge_rects(rs, 1, point_blockers=[point])
        self.assertEqual(out, rs)
        # Unlike a hard core, a nearby point does not impose the 5-um wall rule.
        near = [(0, 2, 1, 3), (20, 2, 21, 3)]
        out, _ = C.merge_rects(near, 1, point_blockers=[point])
        self.assertEqual(out, [(0, 2, 21, 3)])

    def test_native_origin_reservation_covers_body_and_avoids_left_fixed_cell(self):
        import die_trial as D
        class P:
            parts = {"p": {"type": "t"}}
            types = {"t": {"outline_um": [100, 100]}}
            def rect(self, n): return (0, 0, 100, 100)
            def to_type(self, n, q): return q
        # Native body [10,10,11.62,10.27], fixed FT cell ends at x=9.4.
        old, _ = D.island_windows(P(), [((10, 10), "clock")], snap=0)
        new, _ = D.island_windows(P(), [((10, 10), "clock")], snap=0, native_origins=True)
        self.assertLess(old["t"][0][0], 9.4)
        self.assertGreater(new["t"][0][0], 9.4)
        self.assertGreaterEqual(new["t"][0][2], 11.62)


if __name__ == "__main__":
    unittest.main()
