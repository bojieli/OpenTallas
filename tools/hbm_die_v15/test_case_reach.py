import unittest

from case_reach import branches, multicast_relay_ages, xf


class BranchReach(unittest.TestCase):
    def test_far_branch_and_driver_last(self):
        ends = [('near', 'i', (10, 0)), ('far', 'i', (12750, 0)), ('source', 'o', (0, 0))]
        directions = {('source', 'o'): 'OUTPUT', ('near', 'i'): 'INPUT', ('far', 'i'): 'INPUT'}
        bs = branches(ends, directions)
        self.assertEqual([b[2] for b in bs], [10, 12750])
        self.assertEqual(len(bs), 2)

    def test_multiple_drivers_fail_closed(self):
        ends = [('a', 'p', (0, 0)), ('b', 'p', (1, 0))]
        self.assertIsNone(branches(ends, {('a', 'p'): 'OUTPUT', ('b', 'p'): 'OUTPUT'}))

    def test_all_oriented_pin_transforms(self):
        expected = {'R0': (12, 23), 'R90': (27, 22), 'R180': (18, 37), 'R270': (13, 28),
                    'MX': (12, 37), 'MY': (18, 23), 'MXR90': (13, 22), 'MYR90': (27, 28)}
        for orient, result in expected.items():
            with self.subTest(orient=orient):
                self.assertEqual(xf({'x': 10, 'y': 20, 'orient': orient}, 10, 20, 2, 3), result)

    def test_direct_and_two_cycle_multicast_are_not_equal_age(self):
        def edge(a, b):
            return dict(source=[*a, 0, 1], sink=[*b, 0, 1], bits=1)
        c = dict(instances={n: dict(master='hbfd_rly_48_NS' if n.startswith('r') else 'opaque')
                            for n in ('source', 'near', 'far', 'r0', 'r1')},
                 edges=[edge(('source', 'o'), ('near', 'i')), edge(('source', 'o'), ('r0', 'i')),
                        edge(('r0', 'o'), ('r1', 'i')), edge(('r1', 'o'), ('far', 'i'))])
        result = multicast_relay_ages(c)
        self.assertEqual(result['unequal_relay_age'], 1)
        self.assertEqual(result['rows'][0]['min_relay_cycles'], 0)
        self.assertEqual(result['rows'][0]['max_relay_cycles'], 2)
        self.assertIn('UNPROVEN', result['rows'][0]['compiled_equal_age_calendar'])


if __name__ == '__main__':
    unittest.main()
