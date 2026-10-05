"""Negative controls for scoped geometric claims, not a replacement for DRC."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit', ROOT/'tools/w10_allport_access_audit.py')
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class NecessaryAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lef = (ROOT/a.LEF).read_text()
        cls.raw = (ROOT/a.DIR/'inspection.log').read_text()
        cls.baseline = a.audit(cls.lef, cls.raw)

    def test_exhaustive_census_and_named_failure_witnesses(self):
        self.assertEqual(self.baseline['port_instances'], 1152)
        self.assertEqual(sum(r['failed_c8_net_witness'] for r in self.baseline['records']), 2)
        self.assertEqual(self.baseline['classifications']['M4_center_on_track_diagnostic'],
                         {'PROVABLE': 576, 'REFUTED': 576})
        self.assertEqual(self.baseline['classifications']['unextended_port_contains_centered_VIA45_M4'],
                         {'REFUTED': 1152})
        self.assertFalse(self.baseline['full_legal_access_proved'])

    def test_clock_omission_is_rejected(self):
        mutant = self.lef.replace('PIN clk', 'PIN lost_clock').replace('END clk', 'END lost_clock')
        with self.assertRaisesRegex(ValueError, 'census mismatch'):
            a.parse_lef(mutant)

    def test_missing_orientation_is_rejected(self):
        mutant = '\n'.join(l for l in self.raw.splitlines() if not l.startswith('AUDIT|MACRO|') or '|MX|' not in l)
        with self.assertRaisesRegex(ValueError, 'orientation census'):
            a.read_inspection(mutant)

    def test_independent_orientation_coordinates(self):
        known = {'R0': (1000, 2004, 1024, 2028), 'MX': (1000, 2032, 1024, 2056),
                 'MY': (1076, 2004, 1100, 2028), 'R180': (1076, 2032, 1100, 2056)}
        for orient, expected in known.items():
            self.assertEqual(a.transform((0, 4, 24, 28), (100, 60),
                dict(orientation=orient, bbox_nm=[1000, 2000, 1100, 2060])), expected)

    def test_placement_shift_changes_track_witness(self):
        macros, _, _, _, _ = a.read_inspection(self.raw)
        m = next(m for m in macros if m['orientation'] == 'R0')
        old = ' '.join(map(str, m['bbox_nm']))
        new = ' '.join(str(v + (6 if i%2 else 0)) for i, v in enumerate(m['bbox_nm']))
        mutant = self.raw.replace('|R0|'+old, '|R0|'+new)
        result = a.audit(self.lef, mutant)
        self.assertEqual(result['classifications']['M4_center_on_track_diagnostic']['REFUTED'], 864)

    def test_inserted_PDN_conflict_is_refuted_with_witness(self):
        pin = next(r for r in self.baseline['records'] if r['port'] == 'rd_out[171]' and r['orientation'] == 'MX')
        rect = pin['rect_nm']
        mutant = self.raw + '\nAUDIT|PG|VDD|M4|'+' '.join(map(str, rect))+'|wire\n'
        result = a.audit(self.lef, mutant)
        altered = next(r for r in result['records'] if r['port'] == pin['port'] and r['orientation'] == 'MX')
        witness = altered['constraints']['centered_M4_landing_PDN_nonoverlap']
        self.assertEqual(witness['classification'], 'REFUTED')
        self.assertTrue(witness['witness']['collisions'])

    def test_cut_scalar_zero_does_not_clear_advanced_rules(self):
        for r in self.baseline['records']:
            self.assertEqual(r['constraints']['cut_spacing_and_enclosure_rules']['classification'], 'MISSING')

    def test_truncated_query_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'missing completion marker'):
            a.read_inspection(self.raw.replace('AUDIT|COMPLETE', ''))

    def test_missing_PG_via_prevents_false_complete_extraction(self):
        with self.assertRaisesRegex(ValueError, 'incomplete database extraction'):
            a.read_inspection(self.raw+'\nAUDIT|MISSING_PG_VIA|unavailable\n')

    def test_enlarged_cut_breaks_containment(self):
        mutant = self.raw.replace('AUDIT|VIABOX|VIA45|V4|-12 -12 12 12',
                                  'AUDIT|VIABOX|VIA45|V4|-13 -12 13 12')
        result = a.audit(self.lef, mutant)
        self.assertEqual(result['classifications']['unextended_port_contains_centered_V4_cut'],
                         {'REFUTED': 1152})

    def test_power_gap_below_scalar_rule_is_detected(self):
        # Non-overlapping metal can still violate base spacing; an overlap-only
        # audit must not pass this negative control.
        self.assertFalse(a.overlap((0, 0, 24, 24), (47, 0, 71, 24)))
        self.assertEqual(a.gap((0, 0, 24, 24), (47, 0, 71, 24)), 23)
        self.assertLess(a.gap((0, 0, 24, 24), (47, 0, 71, 24)), 24)


if __name__ == '__main__':
    unittest.main(verbosity=2)
