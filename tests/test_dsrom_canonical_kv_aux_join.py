import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('join', ROOT / 'tools/dsrom_canonical_kv_aux_join.py')
join = importlib.util.module_from_spec(spec)
spec.loader.exec_module(join)
INPUTS = ROOT / 'results/uarch/dsrom_canonical_kv_aux_join_20261004/inputs'


class CanonicalJoinTests(unittest.TestCase):
    def setUp(self):
        self.data, self.origins = join.load_inputs(INPUTS)

    def model(self):
        return join.compose(self.data, self.origins)

    def test_actual_census_and_all_rank_provider_copies(self):
        m = self.model()
        self.assertEqual(m['strict_return']['retained_nodes'], 5090)
        self.assertEqual(m['strict_return']['retained_unilateral_nodes'], 384)
        self.assertEqual(m['provider_rank_bindings'], 320)
        self.assertEqual(len(m['per_rank_die']), 324)
        self.assertEqual(m['provisional_stack_rule_total'], 452)
        self.assertTrue(all(r['indexer_projection_policy'].startswith('wk and wq_b local') for r in m['per_rank_die']))

    def test_no_qualification_or_zero_unknown_service_credit(self):
        m = self.model()
        self.assertIsNone(m['KV_capacity_PASS'])
        self.assertFalse(m['entire_shipped_checkpoint_exactonce_PASS'])
        self.assertFalse(m['physical_launch_allowed'])
        self.assertEqual(m['auxiliary']['unqualified_tensors'], 2667)
        self.assertTrue(all(r['service_area_mm2'] is None for r in m['per_rank_die']))
        self.assertIsNone(m['selected_capture_occupancy_and_consumer_deadlines'])

    def test_marker_ranges_share_existing_pair_without_overlap(self):
        p = self.model()['auxiliary']['image_marker_proposal']
        self.assertEqual(p['source_bytes'], 30720)
        self.assertEqual([(t['logical_word_start'], t['logical_word_end_exclusive']) for t in p['tensors']], [(320, 640), (640, 960), (960, 1280)])
        self.assertTrue(all(t['proposed_pair'] == 5050 for t in p['tensors']))
        self.assertEqual(p['new_macros'], 0)
        self.assertFalse(p['placement_qualified'])
        self.assertIsNone(p['physical_die'])

    def test_snapshot_change_rejected_before_composition(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)
            for f in INPUTS.iterdir():
                (p / f.name).write_bytes(f.read_bytes())
            (p / 'inventory.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'source identity'):
                join.load_inputs(p)

    def test_strict_other_inventory_rejected(self):
        self.data['strict_binding_result.json']['input_sha256']['inventory.json'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'strict canonical identity'):
            self.model()

    def test_compact_count_cannot_replace_actual(self):
        self.data['strict_model.json']['retained_nodes'] = 4706
        with self.assertRaisesRegex(ValueError, 'compact census'):
            self.model()

    def test_missing_rank_rejected(self):
        self.data['stage_map.json']['rank_dies'].pop()
        with self.assertRaisesRegex(ValueError, 'rank ownership'):
            self.model()

    def test_wrong_provider_home_rejected(self):
        self.data['providers.json'][0]['stage'] = 80
        with self.assertRaisesRegex(ValueError, 'provider home'):
            self.model()

    def test_provider_overlap_rejected(self):
        self.data['providers.json'][1]['pairs'][0] = self.data['providers.json'][0]['pairs'][0]
        with self.assertRaisesRegex(ValueError, 'provider overlap'):
            self.model()

    def test_marker_encoding_change_rejected(self):
        next(t for t in self.data['auxiliary_obligations.json']['tensors'] if t['tensor'] == 'image_end')['dtype'] = 'F32'
        with self.assertRaisesRegex(ValueError, 'encoding changed'):
            self.model()

    def test_storage_extent_overflow_rejected(self):
        self.data['inventory.json']['rows'] = 1279
        with self.assertRaisesRegex(ValueError, 'word capacity'):
            self.model()

    def test_auxiliary_omission_rejected(self):
        self.data['auxiliary_obligations.json']['tensors'].pop()
        with self.assertRaisesRegex(ValueError, 'auxiliary census'):
            self.model()

    def test_historical_capture_is_not_replicated_to_array(self):
        m = self.model()
        self.assertEqual(set(m['historical_finite_capture']), {'0', '1'})
        self.assertTrue(all(r['replication_count'] is None for r in m['historical_finite_capture'].values()))
        self.assertFalse(m['strict_verdict_lineage']['byte_identical'])
        self.assertIn('historical generic verdict', m['strict_verdict_lineage']['current_binding_explicitly_joins_original'])


if __name__ == '__main__':
    unittest.main()
