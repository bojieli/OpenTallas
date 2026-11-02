import random
import unittest
from taps import assign as reference
from vector_tap_assign import assign


class ExactAssignment(unittest.TestCase):
    def check(self, taps, sinks, cap, extra, radius=None):
        self.assertEqual(reference(taps, sinks, cap, extra, radius), assign(taps, sinks, cap, extra, radius))

    def test_nearest_ties(self):
        self.check([('a', 0, 0), ('b', 2, 0)], [(1, 0, 1)]*6, 3, 2)

    def test_capacity_target_order(self):
        self.check([('a', 0, 0), ('b', 4, 0), ('c', 0, 4)], [(0, 0, 1)]*9, 3, 5)

    def test_radius_stuck(self):
        self.check([('a', 0, 0), ('b', 4, 0)], [(0, 0, 1)]*8, 3, 4, 3)

    def test_fractional_overshoot(self):
        self.check([('a', 0, 0), ('b', 4, 0), ('c', 0, 4)], [(0, 0, .7)]*11, 2, 5, 5)

    def test_empty(self):
        self.check([], [], 3, 5)
        self.check([('a', 0, 0)], [], 3, 5)

    def test_randomized_reference(self):
        rng = random.Random(881)
        for _ in range(100):
            taps = [(str(j), rng.randrange(20)/4, rng.randrange(20)/4) for j in range(rng.randrange(1, 9))]
            sinks = [(rng.randrange(20)/4, rng.randrange(20)/4, rng.choice([1, 1, .7, 1.1])) for _ in range(rng.randrange(1, 60))]
            self.check(taps, sinks, rng.choice([2, 3, 8]), rng.choice([0, 2, 5]), rng.choice([None, 2, 6]))


if __name__ == '__main__':
    unittest.main()
