"""Regression: current cluster census must never confer parent timing closure."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_sta as D


class PartitionCoverage(unittest.TestCase):
    def test_current_capture_is_not_legacy_alias(self):
        self.assertIn('dsfd_capt_x8_dual', D.PARTS['dsfd_sp_capture_c'])
        self.assertIn('dsfd_capt_cd', D.PARTS['dsfd_sp_capture_c'])
        self.assertNotIn('dsfd_capt_x', D.PARTS['dsfd_sp_capture_c'])
        self.assertIn('dsfd_capt_x', D.PARTS['dsfd_sp_capture'])

    def test_all_corner_coverage_remains_interim(self):
        parts = {'cluster': ('a', 'b')}
        idx = {c: {'a': ('a.lib', 'closed'), 'b': ('b.lib', 'closed')}
               for c in ('ss', 'tt', 'ff')}
        r = D.partition_record('cluster', idx, parts)
        self.assertEqual(r['tiles_closed'], ['a', 'b'])
        self.assertFalse(r['parent_qualified'])
        self.assertEqual(r['timing_model'], 'interim_pin_registered')
        del idx['ff']['b']
        self.assertEqual(D.partition_record('cluster', idx, parts)['tiles_closed'], ['a'])
        idx['ff']['a'] = ('a.lib', 'assembled')
        self.assertEqual(D.partition_record('cluster', idx, parts)['tiles_closed'], [])

    def test_modern_multiroot_parent_refuses_scalar_child_mean(self):
        mi = {'dsfd_capt_x8_dual': {'ss': 300, 'ff': 200, 'tt': 250}}
        with self.assertRaisesRegex(ValueError, 'per-pin insertion'):
            D.arcs_insertion('dsfd_sp_capture_c', 'assembled', mi)
        # An interim diagnostic does not pretend to carry child insertion.
        self.assertEqual(D.arcs_insertion('dsfd_sp_capture_c', 'partitioned', mi), [0, 0, 0])

    def test_unknown_parent_does_not_inherit_inventory(self):
        self.assertEqual(D.partition_record('dsfd_sp_capture_unknown', {}), {})


if __name__ == '__main__':
    unittest.main()
