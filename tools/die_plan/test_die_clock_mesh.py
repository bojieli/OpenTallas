#!/usr/bin/env python3
"""unit tests: tools/die_plan/die_clock_mesh.py site helpers (python3 -m pytest tools/die_plan/test_die_clock_mesh.py)"""
import sys
import unittest
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


if __name__ == "__main__":
    unittest.main()
