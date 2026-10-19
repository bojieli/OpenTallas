"""Regression for kvs14p real-case MY pin-lattice failure."""
import unittest

from kv_lane_orientation import adapt, origin_rules


def macro(mixed=True):
    pins = [dict(name='ck', use='SIGNAL', rects=[('M3', (8100, 0, 8118, 37))])]
    if mixed:
        pins.append(dict(name='tie_hi', use='SIGNAL', rects=[('M5', (9216, 12876, 9240, 12960))]))
    return dict(name='lane', W=12960, H=12960, pins=pins)


class OrientationTest(unittest.TestCase):
    def test_mixed_clock_strap_lattices_adapt_x_only(self):
        text = 'ot_mts::place [$_blk findInst hop] 1 2 R180\n'
        placed, report = adapt(text, {'hop': ('lane', '')}, {'lane': macro()})
        self.assertIn('1 2 MX', placed)
        self.assertEqual(report['changes'][0]['max_pin_x_displacement_um'], 12.96)
        self.assertFalse(origin_rules(macro(), 'MY')['x']['legal_origins_mod_joint_nm'])

    def test_single_lattice_keeps_legal_mirror(self):
        text = 'ot_mts::place [$_blk findInst hop] 1 2 MY\n'
        placed, report = adapt(text, {'hop': ('lane', '')}, {'lane': macro(False)})
        self.assertEqual(placed, text)
        self.assertEqual(report['changes'], [])

    def test_offtrack_mutant_refused(self):
        m = macro()
        m['pins'][0]['rects'].append(('M3', (8101, 100, 8119, 137)))
        with self.assertRaisesRegex(ValueError, 'no legal orientation'):
            adapt('ot_mts::place [$_blk findInst hop] 1 2 R0', {'hop': ('lane', '')}, {'lane': m})

    def test_missing_placement_refused(self):
        with self.assertRaisesRegex(ValueError, 'placement missing'):
            adapt('', {'hop': ('lane', '')}, {'lane': macro()})


if __name__ == '__main__':
    unittest.main()
