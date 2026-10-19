"""Physical reset-tree invariants, including a blocked channel requiring a detour."""
import unittest

import kv_child_rst as R


class ResetTreeTest(unittest.TestCase):
    def check_tree(self, rect, obstacles, loads, driver):
        stations, assignment = R.plan('test', rect, obstacles, loads, driver, lambda _: 'ck')
        by = {s['name']: s for s in stations}
        self.assertEqual(set(assignment), {key for key, _ in loads})
        for s in stations:
            self.assertLessEqual(s['hop_um'], R.HOP + .05)
            self.assertLessEqual(len(s['members']), R.FAN)
            parent = by.get(s['parent'])
            self.assertEqual(s['depth'], 1 if parent is None else parent['depth'] + 1)
            for x0, y0, x1, y1 in obstacles:
                self.assertFalse(min(s['x'] + R.STN, x1) > max(s['x'], x0)
                                 and min(s['y'] + R.STN, y1) > max(s['y'], y0))
        for key, xy in loads:
            s = by[assignment[key]]
            self.assertFalse(s['far'])
            self.assertLessEqual(R._d((s['x'] + R.STN / 2, s['y'] + R.STN / 2), xy), R.LEAF_R + .01)
        return stations

    def test_open_channel(self):
        self.check_tree((0, 0, 1400, 300), [], [('pin', (1300, 150))], (50, 150))

    def test_pocket_needs_route_away_from_target(self):
        # The wall exceeds the hop budget. The source must move north before it can reach the east-side pin.
        stations = self.check_tree((0, 0, 1200, 1200), [(400, 0, 850, 900)],
                                   [('pin', (900, 450))], (350, 450))
        self.assertTrue(any(s['y'] >= 900 for s in stations))

    def test_no_route_fails_closed(self):
        with self.assertRaises(ValueError):
            R.plan('sealed', (0, 0, 1200, 1200), [(400, 0, 850, 1200)],
                   [('pin', (900, 450))], (350, 450), lambda _: 'ck')


if __name__ == '__main__':
    unittest.main()
