#!/usr/bin/env python3
"""Check actual square geometry, ownership mapping and preserved old defaults."""
import importlib.util
from pathlib import Path
import unittest
import selector_square as S

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('tiles', ROOT/'tools/budgets/tiles.py')
B = importlib.util.module_from_spec(spec)
spec.loader.exec_module(B)


class SelectorSquare(unittest.TestCase):
    def test_actual_shape_and_no_assumed_mirror(self):
        m = S.build(ROOT)
        self.assertFalse(m['qualified'])
        self.assertEqual(m['local_outline_um'], [1086.544, 604.8])
        self.assertAlmostEqual(m['existing_slab_height_deficit_um'], 282.984)
        self.assertEqual({t['orient'] for t in m['tiles']}, {'R0'})
        self.assertEqual(m['internal_bundle_bits'], 5144)
        for a in m['tiles']:
            aw, ah = (432, 280.8) if a['master']=='dsfd_selt_q2' else (129.6,319.68)
            for b in m['tiles']:
                if a is b: continue
                bw, bh = (432,280.8) if b['master']=='dsfd_selt_q2' else (129.6,319.68)
                self.assertFalse(a['x'] < b['x']+bw and b['x'] < a['x']+aw and
                                 a['y'] < b['y']+bh and b['y'] < a['y']+ah)
        self.assertGreater(max(b['length_um_max'] for b in m['bundles']), 504)
        self.assertEqual(m['die_ports']['lanes']['iNE'], ['u_q3','lane'])
        self.assertEqual(m['latency']['measured_increment_over_127_cycles'],47)

    def test_one_row_actual_m8_capacity(self):
        import selector_one_row as R
        m=R.build(ROOT)
        self.assertEqual(m['track_pitch_um'], .08)
        self.assertEqual(m['outline_um'], [2036.944,1006.56])
        self.assertGreaterEqual(m['tracks_capacity_lower_bound'],5144)
        self.assertEqual(m['station_instances'],107)
        self.assertFalse(m['qualified'])
        self.assertEqual(m['latency']['credits'],4)

    def test_budget_uses_unimplemented_direct_seam(self):
        legacy = B.build(ROOT)
        square = B.build(ROOT, selector_square=True)
        self.assertIn('dsfd_selt_q', legacy)
        self.assertNotIn('dsfd_selt_q2', legacy)
        self.assertNotIn('dsfd_selt_q', square)
        q=square['dsfd_selt_q2']
        self.assertEqual(q['size_um'],[432,280.8])
        self.assertEqual(q['qualification'],'UNQUALIFIED')
        self.assertGreater(q['edges'][1]['length_um'],504)
        self.assertEqual(square['dsfd_selt_c']['qualification'],'UNQUALIFIED')


if __name__ == '__main__': unittest.main()
