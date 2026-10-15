"""Independent geometry guard checks for the advisory placement search."""
import unittest
from placement_repack import gap, overlap, relays, validate


class GeometryGuards(unittest.TestCase):
    def test_contact_is_legal_but_positive_area_overlap_is_not(self):
        a = dict(n='a', x=0, y=0, w=10, h=20)
        b = dict(n='b', x=10, y=0, w=10, h=20)
        self.assertFalse(overlap(a, b))
        b['x'] = 9.999
        self.assertEqual(validate([a, b], dict(w=100, h=100)), [['overlap', 'a', 'b']])

    def test_outside_and_manhattan_reach(self):
        a = dict(n='a', x=0, y=0, w=10, h=20)
        b = dict(n='b', x=500, y=510, w=10, h=20)
        self.assertEqual(gap(a, b), 980)
        self.assertEqual(relays(a, b), 1)
        b['x'] += .001
        self.assertEqual(relays(a, b), 2)
        self.assertIn(['outside', 'b'], validate([a, b], dict(w=500, h=500)))


if __name__ == '__main__':
    unittest.main()
