#!/usr/bin/env python3
"""unit tests: tools/die_plan/die_clock_mesh.py site helpers (python3 -m pytest tools/die_plan/test_die_clock_mesh.py)"""
import sys
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_clock_mesh as CM  # noqa: E402


class Box:
    """keep-out index stand-in: one blocked rect."""
    def __init__(self, r):
        self.r = r

    def hit(self, x, y, m=0.0):
        x0, y0, x1, y1 = self.r
        return x0 - m <= x <= x1 + m and y0 - m <= y <= y1 + m


class T(unittest.TestCase):
    def test_leg_sites_free_leg_equal_hops(self):
        out = dict(unplaced=[])
        pts = CM.leg_sites(Box((-10, -10, -9, -9)), (0, 0), (2000, 0), 450.0, out, "h0")
        xs = [0.0] + [p[0][0] for p in pts] + [2000.0]
        hops = [b - a for a, b in zip(xs, xs[1:])]
        self.assertEqual(len(pts), 4)
        self.assertLessEqual(max(hops), 450.0 + 1e-6)
        self.assertLess(max(hops) - min(hops), 1.0)

    def test_leg_sites_blocked_never_exceeds_seg_on_leg(self):
        out = dict(unplaced=[])
        pts = CM.leg_sites(Box((300, -50, 700, 50)), (0, 0), (2000, 0), 450.0, out, "h0")
        xs = [0.0] + [p[0][0] for p in pts] + [2000.0]
        self.assertTrue(all(not (300 - 3 <= x <= 700 + 3) for x in xs[1:-1]))
        self.assertLessEqual(max(b - a for a, b in zip(xs, xs[1:])), 450.0 + 1e-6)

    def test_stub_foot_shortest(self):
        xs, ys = [100.0, 300.0, 500.0], [100.0, 300.0, 500.0]
        q, d, axis, i, j = CM.stub_foot(Box((0, 280, 600, 320)), xs, ys, 290.0, 310.0, 500.0)
        self.assertIsNotNone(q)
        self.assertEqual((axis, i), (1, 1))          # the M8 strap y=300 is blocked; M9 x=300 slid off the box
        self.assertLessEqual(abs(q[0] - 290) + abs(q[1] - 310), 30.0)

    def test_region_boxes_follow_htree_bisection(self):
        R = CM.region_boxes(8, 8, 3, W=800.0, H=800.0)
        self.assertEqual(len(R), 8)
        cells = {(i, j) for g in R for i in range(g["i0"], g["i1"]) for j in range(g["j0"], g["j1"])}
        self.assertEqual(len(cells), 64)                       # a partition of the intersection grid
        for g in R:                                            # region tag = the H-tree tag prefix of its members
            for i in range(g["i0"], g["i1"]):
                for j in range(g["j0"], g["j1"]):
                    self.assertTrue(CM.htree_tag(i, j, 8, 8).startswith(g["tag"]))
        self.assertEqual(R[0]["box_um"], [0.0, 0.0, 200.0, 400.0])   # x, y, x halvings
        self.assertEqual(CM.region_boxes(8, 8, 0)[0]["tag"], "h")

    def test_free_along_bounds(self):
        K = Box((90, -5, 110, 5))
        q, d = CM.free_along(K, (100.0, 0.0), 0, 50.0)
        self.assertIsNotNone(q)
        q, d = CM.free_along(K, (100.0, 0.0), 0, 50.0, bounds=(0.0, 100.0))
        self.assertLess(q[0], 90.0)                            # never slides past the region's strap end

    def test_stub_foot_region_box(self):
        xs, ys = [100.0, 300.0, 500.0, 700.0], [100.0, 300.0, 500.0, 700.0]
        far = Box((-10, -10, -9, -9))
        q, d, axis, i, j = CM.stub_foot(far, xs, ys, 410.0, 410.0, 500.0)
        self.assertTrue(i >= 2 or j >= 2)                      # unconstrained: the nearer x=500 / y=500 straps
        q, d, axis, i, j = CM.stub_foot(far, xs, ys, 410.0, 410.0, 500.0, box=(0, 2, 0, 2))
        self.assertTrue(q[0] <= 300.0 + 1e-6 and q[1] <= 300.0 + 1e-6)   # region box: own straps, own extent
        self.assertTrue(i < 2 and j < 2)

    def test_mesh_net_names(self):
        self.assertEqual(CM.mesh_net(None), "ck_mesh")         # default (no --regions) unchanged
        self.assertEqual(CM.mesh_net(3), "ck_mesh_r3")

    def test_region_edge_strap_reaches_legal_driver_without_crossing_boundary(self):
        xs, ys = [100., 300., 500., 700.], [100., 300., 500., 700.]
        g = dict(i0=0, i1=2, j0=0, j1=4, strap_box_um=[.214, .214, 399.786, 799.786])
        obstacle = Box((200, -20, 340, 820))
        q, _ = CM.free_along(obstacle, (300, 100), 0, 60, bounds=(100, 300))
        self.assertIsNone(q)
        q, _ = CM.free_along(obstacle, (300, 100), 0, 60, bounds=CM.strap_bounds(g, xs, ys, 0))
        self.assertGreater(q[0], 340.)
        self.assertLess(q[0], 400.)
        foot, *_ = CM.stub_foot(obstacle, xs, ys, 350, 110, 60, box=(0, 2, 0, 4), extent=g["strap_box_um"])
        self.assertGreater(foot[0], 340.)
        self.assertLess(foot[0], 400.)

    def test_clock_cells_are_physical_obstacles_and_abutment_is_legal(self):
        K = CM.DC.KeepIndex([], die=(100., 100.))
        cells = dict(a=dict(x=10., y=10.), b=dict(x=10.+CM.BUF_W, y=10.))
        CM.reserve_cell(K, "a", cells["a"])
        self.assertIsNotNone(K.hit(10.5, 10.1, m=0.))
        self.assertEqual(CM.placement_overlaps(cells), [])
        cells["b"]["x"] -= .054
        self.assertEqual(CM.placement_overlaps(cells), [["a", "b"]])

    def test_core_offsets_compare_sinks_at_each_corner(self):
        M = {"taps": [dict(part="p", tap="core", port="tc", early_ps=100),
                      dict(part="p", tap="ordinary", port="to", early_ps=0)]}
        offsets = {("p", "core"): {"TT": 100, "FF": 70}}
        for corner, core_arrival in (("TT", 900), ("FF", 930)):
            late, early, _ = CM.sink_arrivals(M, {"tc": (core_arrival, core_arrival - 5, 10),
                                                 "to": (1000, 995, 10)}, corner, offsets)
            self.assertEqual(late["tc"], late["to"])
            self.assertEqual(early["tc"], early["to"])

    def test_mixed_stub_cells_preserve_the_real_library(self):
        cells = {"s": dict(kind="stub", lib="BUFx2_ASAP7_75t_R"), "d": dict(kind="drv")}
        nets = [dict(name="root", drv="port:root", loads=["d"]),
                dict(name="ckm_w_s", drv="s", loads=["port:t_p__clk"])]
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "clock.v"
            CM.write_verilog(cells, nets, [("output", "t_p__clk")], path)
            self.assertIn("BUFx2_ASAP7_75t_R s", path.read_text())
            self.assertIn(CM.BUF + " d", path.read_text())

    def test_regional_diagnostic_never_qualifies_missing_landings(self):
        M = dict(meta={"unplaced": 0}, unplaced=[])
        corners = {c: dict(verdict="PASS", landed_verdict="PASS") for c in ("TT", "FF")}
        self.assertEqual(CM.regional_qualification(M, corners, 3)["release_verdict"], "BLOCKED")
        self.assertEqual(CM.regional_qualification(M, corners, 0)["release_verdict"], "CLOCK-PASS")
        M["unplaced"] = [[0, 0]]
        self.assertEqual(CM.regional_qualification(M, corners, 0)["release_verdict"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
