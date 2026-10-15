import unittest
from fractions import Fraction
from link_boundary_audit import audit, read_source, FEC, LINK


class ActualBoundaryCapacity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fec = read_source('cbd4a9fb7', FEC)[0]
        cls.link = read_source('b8cf4feda', LINK)[0]

    def test_actual_one_frame_per_cycle_cannot_fit(self):
        r = audit(self.fec, self.link, Fraction(1))
        self.assertFalse(r['necessary_capacity_pass'])
        self.assertFalse(r['direct_wires_compatible'])
        self.assertEqual(r['ideal_packed_superframe'], {'frames':487, 'transport_cycles':612})

    def test_slower_reserved_rate_only_passes_capacity(self):
        r = audit(self.fec, self.link, Fraction(1, 2))
        self.assertTrue(r['necessary_capacity_pass'])
        self.assertFalse(r['qualified'])
        self.assertFalse(r['direct_wires_compatible'])

    def test_source_width_change_is_not_silently_ignored(self):
        widened = self.fec.replace(b'[486:0]tx', b'[611:0]tx').replace(b'[486:0]rx', b'[611:0]rx')
        r = audit(widened, self.link, Fraction(1))
        self.assertTrue(r['necessary_capacity_pass'])
        self.assertTrue(r['direct_wires_compatible'])
        self.assertFalse(r['qualified'])


if __name__ == '__main__':
    unittest.main()
