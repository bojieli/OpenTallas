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


if __name__ == "__main__":
    unittest.main()
