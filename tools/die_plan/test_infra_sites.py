#!/usr/bin/env python3
"""unit tests: tools/die_plan/infra_sites.py (INFRA-SITE SUFFICIENCY gate; python3 -m pytest)"""
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))
import infra_sites as IS  # noqa: E402


class T(unittest.TestCase):
    def test_intervals(self):
        self.assertEqual(IS.union([(0, 2), (1, 3), (5, 6)]), [(0, 3), (5, 6)])
        self.assertEqual(IS.subtract([(0, 10)], [(2, 4), (8, 12)]), [(0, 2), (4, 8)])
        # segment running right-to-left: parameters measured from a
        self.assertEqual(IS.seg_cover((10, 0), (0, 0), [(2, -1, 4, 1)]), [(6.0, 8.0)])
        self.assertEqual(IS.seg_cover((0, 0), (0, 10), [(-1, 3, 1, 5)]), [(3.0, 5.0)])

    def test_gap_runs_across_corner_and_resets_at_sites(self):
        site = lambda a, b: IS.seg_cover(a, b, [(-1, -1, 1, 1), (99, 99, 101, 101)])  # noqa: E731
        g, mid, *_ = IS.poly_gap([(0, 0), (100, 0), (100, 100)], site)
        self.assertAlmostEqual(g, 198.0)                      # blocked from x=1 round the corner to y=99
        site2 = lambda a, b: IS.seg_cover(a, b, [(-1, -1, 1, 1), (40, -1, 60, 1), (99, 99, 101, 101)])  # noqa: E731
        self.assertAlmostEqual(IS.poly_gap([(0, 0), (100, 0), (100, 100)], site2)[0], 139.0)

    def test_route_detours_through_soft_column(self):
        box = (0, 0, 1000, 2000)
        cores = [(0, 500, 450, 1500, "u_a", "A0"), (550, 500, 1000, 1500, "u_b", "A0")]
        r = IS.route_leg((300, 2000), (300, 0), box, cores, [], 405, 405)
        self.assertGreater(r["straight_gap"], 405)                 # straight down crosses 1000 um of core
        self.assertLessEqual(r["gap"], 405)                       # Z through the x=450..550 column
        self.assertLessEqual(r["len"] - r["manhattan"], 405 + 1e-6)
        r0 = IS.route_leg((300, 2000), (300, 0), box, cores, [], 405, 0)
        self.assertGreater(r0["gap"], 405)                        # no detour allowed -> fails closed
        bays = [(0, 990, 450, 1010, "u_a", "A0")]                 # declared in-core bay mid-core
        r1 = IS.route_leg((300, 2000), (300, 0), box, cores, bays, 405, 0)
        self.assertLessEqual(r1["gap"], 500)
        self.assertLess(r1["gap"], r0["gap"])

    def test_core_bays_follow_core_orient(self):
        t = dict(hard_cores=[dict(inst="u", module="m", origin_um=[100, 0], outline_um=[400, 1000], orient="MX",
                                  bays_um=[[0, 100, 400, 110]])])
        (x0, y0, x1, y1, *_), = IS.core_bays(t, None)
        self.assertEqual((x0, y0, x1, y1), (100, 890, 500, 900))
        self.assertEqual(len(IS.core_bays(t, {"m": [[0, 0, 10, 10]]})), 2)

    def test_free_square_at_channel_cross(self):
        # QC cbf_q00 geometry: A0 columns x86.4-544.3 / 691.2-1149.1, rows y77.8-1235.5 / 1382.4-2540.2
        cores = [dict(inst=f"u{i}", module="a0", origin_um=[x, y], outline_um=[457.92, 1157.76])
                 for i, (x, y) in enumerate([(86.4, 77.76), (691.2, 77.76), (86.4, 1382.4), (691.2, 1382.4)])]
        t = dict(outline_um=[1235.52, 2609.28], hard_cores=cores)
        s = IS.free_square(t, (622.08, 1304.64))
        self.assertAlmostEqual(s, 2 * min(622.08 - 544.32, 1304.64 - 1235.52), places=3)

    def test_stack_limit_uses_pg_and_tracks(self):
        P = SimpleNamespace(layers={"M7": {"dir": "V", "pitch_um": 0.064}, "M8": {"dir": "H", "pitch_um": 0.08},
                                    "M9": {"dir": "V", "pitch_um": 0.08}})
        grid = [dict(layer="M8", width_um=0.48, pitch_um=8.64, nets=["VDD", "VSS"]),
                dict(layer="M9", width_um=0.48, pitch_um=8.64, nets=["VDD", "VSS"])]
        f = IS.die_free_frac(P, "M8", grid, None)
        self.assertAlmostEqual(f, 1 - 2 / 8.64 * 7 * 0.08, places=6)
        self.assertAlmostEqual(IS.die_free_frac(P, "M9", grid, {"M9": {"all": 0.3}}), 0.7)
        lim, layer, free = IS.stack_limit(P, grid, None, 0.25, 0.5)
        self.assertEqual(layer, "M8")
        self.assertEqual(lim, int(0.5 * free["M8"]))

    def test_lane_for_die(self):
        self.assertEqual(IS.lane_for("qwen_compute"), "QC-SU-LAT")
        self.assertEqual(IS.lane_for("s81_head"), "HEAD-CORE-LAT")
        self.assertEqual(IS.lane_for("hbm_generic"), "HBM-CORE-LAT")
        self.assertEqual(IS.lane_for("s81"), "S81-CORE-LAT")


if __name__ == "__main__":
    unittest.main()


def test_plan_without_mesh_still_builds_island_geometry():
    import schema as S
    p = S.Plan(S.load(Path(__file__).parent / "examples/tiny_plan.json"))
    report = IS.run(p, mesh_dir=None, with_reset=False)
    assert report["island_instances"]
    assert report["summary"]["checks"]["htree_snap"] == "NOT RUN"
