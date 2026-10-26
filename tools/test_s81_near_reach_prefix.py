#!/usr/bin/env python3
"""Reach pruning must preserve every legal placement and the first chosen spot."""
import random
import unittest
from unittest.mock import patch
import dsrom_s81_fulldie as G

class ReachPrefixTests(unittest.TestCase):
    def test_every_discarded_candidate_is_impossible(self):
        rng = random.Random(19)
        for i in range(24):
            span, rows = (600., 60) if i % 2 else (1200., 120)
            step = rng.choice((32.4, 45.36, 82.08))
            cx, cy = rng.uniform(300, 1500), rng.uniform(300, 1500)
            w, h = rng.choice(((34.56, 30.24), (86.4, 64.776), (200., 100.)))
            prev = (cx + rng.uniform(-250, 250), cy + rng.uniform(-250, 250))
            nxt = (cx + rng.uniform(-250, 250), cy + rng.uniform(-250, 250))
            allowed = [(cx - 400, cy - 100, cx + 400, cy + 100)]
            horiz = bool(i % 3)
            original = G._near_cands(span, rows, step)
            prefix = G._near_reachable_prefix(original, span, rows, step, cx, cy, w, h,
                                              allowed, prev, 400., nxt, 500., horiz)
            self.assertEqual(prefix, original[:len(prefix)])
            for a, c in original[len(prefix):]:
                dx, dy = (a, c) if horiz else (c, a)
                x, y = G.dn(cx + dx - w / 2, G.GX), G.dn(cy + dy - h / 2, G.GY)
                pt = (x + w / 2, y + h / 2)
                legal = (G._inside((x, y, x + w, y + h), allowed)
                         and G._mh(prev, pt) <= 400. and G._mh(nxt, pt) <= 500.)
                self.assertFalse(legal, (i, a, c))

    def test_axis_filter_preserves_order_and_all_legal_offsets(self):
        rng = random.Random(1417)
        for case in range(30):
            horiz = bool(case % 2)
            cx, cy = rng.uniform(100, 1000), rng.uniform(100, 1000)
            w, h = rng.choice(((34.56, 30.24), (201.288, 203.016)))
            allowed = [(0., 0., 1500., 1200.), (500., 1200., 1600., 2000.)]
            prev = (cx + rng.uniform(-300, 300), cy + rng.uniform(-300, 300))
            nxt = (cx + rng.uniform(-300, 300), cy + rng.uniform(-300, 300))
            original = G._near_cands(1200., 120, 36.72)
            actual = list(G._near_reachable_candidates(original, 1200., 120, 36.72,
                       cx, cy, w, h, allowed, prev, 400., nxt, 500., horiz))
            subset = set(actual)
            self.assertEqual(actual, [pair for pair in original if pair in subset])
            for a, c in original:
                if (a, c) in subset:
                    continue
                dx, dy = (a, c) if horiz else (c, a)
                x, y = G.dn(cx + dx - w / 2, G.GX), G.dn(cy + dy - h / 2, G.GY)
                pt = (x + w / 2, y + h / 2)
                self.assertFalse(G._inside((x, y, x + w, y + h), allowed)
                                 and G._mh(prev, pt) <= 400. and G._mh(nxt, pt) <= 500.)

    def test_same_first_placement_with_obstacles_and_both_reaches(self):
        for horiz in (False, True):
            for reach in (35., 100., 500.):
                placer = G.Placer({'insts': []})
                placer.occ.add((400., 250., 550., 380.))
                args = (450., 300., 34.56, 30.24, [(0., 0., 700., 650.)])
                kw = dict(prev=(460., 325.), nxt=(400., 360.), nreach=150., reach=reach,
                          horiz=horiz, span=1200., rows=120)
                with patch.object(G, '_near_reachable_candidates', lambda candidates, *args: candidates):
                    expected = placer.near(*args, **kw)
                actual = placer.near(*args, **kw)
                self.assertEqual(actual, expected, (horiz, reach))

if __name__ == '__main__':
    unittest.main()
