import importlib.util
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('constraints', HERE / 'readiness_constraints.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
R = HERE.parents[2] / 'results/rtl/s81_final_ffn_source_1131'


class ReadinessTest(unittest.TestCase):
    def setUp(self):
        self.receipt = json.loads((R / 'native_readlease64/check.json').read_text())

    def test_measured_native_boundary_and_early_controls(self):
        offsets = m.measured_reads(self.receipt)
        for issue, safe, violations in ((24, True, 0), (23, False, 2), (0, False, 62)):
            case = json.loads((R / 'native_readlease64/cases.json').read_text())[f'issue_{issue}']
            result = m.replay_log((R / f'native_readlease64/issue_{issue}.log').read_text(), case['rdreg'], offsets)
            self.assertEqual(result['minimum_registered_CV'], 180)
            self.assertEqual(result['safe'], safe)
            self.assertEqual(len(result['violations']), violations)

    def test_missing_bank_is_rejected(self):
        self.receipt['safe']['read_events'].pop()
        with self.assertRaises(ValueError):
            m.measured_reads(self.receipt)

    def test_conditional_epoch_is_preserved(self):
        join = json.loads((R / 'event_join/check.json').read_text())
        result = m.compile_constraints(join, self.receipt)
        self.assertEqual(len(result['source_pairs']), 2)
        self.assertFalse(result['global_leases_qualified'])
        for old, new in zip(join['RD_pairs'], result['source_pairs']):
            self.assertIsNone(new['production_registered_CV'])
            for alternative in new['alternatives']:
                for word, term in zip(old['word_events'], alternative['all_word_lower_bounds']):
                    self.assertEqual(term['source_epoch'], word['unknown_epoch'])
                    boundary = word['composed_commit_edge_n'] + 1 - alternative['actual_SRAM_read_offset_from_CV']
                    self.assertEqual(term['minimum_CV_relative_to_source_epoch'], boundary)
                    self.assertGreater(boundary + alternative['actual_SRAM_read_offset_from_CV'], word['composed_commit_edge_n'])
                    self.assertEqual(boundary - 1 + alternative['actual_SRAM_read_offset_from_CV'], word['composed_commit_edge_n'])


if __name__ == '__main__':
    unittest.main()
