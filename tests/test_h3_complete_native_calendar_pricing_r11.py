import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('pricing_r11', ROOT/'tools/h3_complete_native_calendar_pricing_r11.py')
M = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(M)


class PricingCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = M.load_inputs(M.DEFAULT)
        cls.snapshot = json.loads(cls.inputs['graph'])

    def test_cold_model_exact(self):
        self.assertEqual(M.build(self.inputs), json.loads((M.DEFAULT/'model.json').read_text()))

    def test_single_segment_tail_once(self):
        c = M.local_select_cost(10, 56, 66)
        self.assertEqual(c['issue'] + c['depth'], 66)
        self.assertFalse(c['stream'])

    def test_segment_finite_queues(self):
        c = M.local_select_cost(10, 56, 66, 3, 1)
        self.assertEqual(c['issue'] + c['depth'], 198)

    def test_parallel_units_still_price_input(self):
        self.assertEqual(M.local_select_cost(10, 56, 66, 3, 3)['issue'], 30)

    def test_invalid_occupancy(self):
        with self.assertRaises(ValueError):
            M.local_select_cost(10, 56, 65)

    def test_literal_select_successor(self):
        class G:
            def add(self, name, deps, **kw):
                return kw
        class Ops:
            g = G()
            p = type('P', (), {'select_units': 1, 'tselect_units': 1})()
            mb = 1
            bctrl = 0
            cyc = staticmethod(float)
        timing = dict(lanes=16, cand_score_lanes=16, cand_lanes=16, cand_front=5, lat0=36)
        fn = M.local_select_successor(self.inputs['decoder'].decode(), timing,
                                     lambda n: 2*((n+15)//16)+36)
        row = fn(Ops(), 'test', [], 0, n=160, k=16)
        self.assertEqual(row['issue'], 10)
        self.assertEqual(row['depth'], 56)
        Ops.mb = 3
        row = fn(Ops(), 'test', [], 0, n=160, k=16)
        self.assertEqual(row['issue'] + row['depth'], 198)

    def test_measured_lat0_cohort_reuse(self):
        class G:
            def add(self, name, deps, **kw):
                return kw
        class Ops:
            g = G()
            p = type('P', (), {'select_units': 1, 'tselect_units': 1})()
            mb = 2
            bctrl = 0
            cyc = staticmethod(float)
        timing = dict(lanes=16, cand_score_lanes=16, cand_lanes=16, cand_front=5, lat0=65)
        fn = M.local_select_successor(self.inputs['decoder'].decode(), timing,
                                     lambda n: 2*((n+15)//16)+65)
        row = fn(Ops(), 'test', [], 0, n=160, k=16)
        self.assertEqual(row['depth'], 85)
        self.assertEqual(row['issue'] + row['depth'], 2*(10+85))

    def test_campaign_direct_select_scope(self):
        r = M.build(self.inputs)
        rows = r['literal_direct_select_cases']
        self.assertEqual(len(rows), 9)
        self.assertTrue(all(n['old_issue_cycles'] > n['corrected_issue_cycles'] for n in rows))
        self.assertTrue(all(not n['scorer_overlap'] for n in rows))

    def test_select_changed_source_refuses(self):
        source = self.inputs['decoder'].decode().replace('math.ceil(self.mb / units) * occ', '0')
        with self.assertRaises(ValueError):
            M.local_select_successor(source, {}, None)

    def test_candidate_real_consumers(self):
        fixed, names = M.bind_candidates(self.snapshot['nodes'], self.snapshot['config'])
        self.assertEqual(names, [f'L{i}.attn.idx.score' for i in (24,28,32,36)])
        for name in names:
            self.assertIn('L20.attn.cand.final', fixed[name]['deps'])
        self.assertNotIn('L20.attn.cand.final', self.snapshot['nodes'][names[0]]['deps'])

    def test_missing_candidate_refuses(self):
        nodes = copy.deepcopy(self.snapshot['nodes'])
        del nodes['L20.attn.cand.final']
        with self.assertRaises(ValueError):
            M.bind_candidates(nodes, self.snapshot['config'])

    def test_no_candidate_consumer_refuses(self):
        c = copy.deepcopy(self.snapshot['config'])
        for mode in c['modes'].values():
            mode['mode'] = 'reuse'
        with self.assertRaises(ValueError):
            M.bind_candidates(self.snapshot['nodes'], c)

    def test_literal_pair_contract(self):
        c = M.emitter_contract(self.inputs['emitter'].decode())
        self.assertEqual(len(c['gate_up']), 2)
        self.assertEqual(len(c['attention']), 2)

    def test_pair_removal_refuses(self):
        source = self.inputs['emitter'].decode().replace('self.linq(lay.qmat[(L, "wkv")]', 'self.me(lay.qmat[(L, "wkv")]')
        with self.assertRaises(ValueError):
            M.emitter_contract(source)

    def test_all_pairs_and_dependencies(self):
        r = M.build(self.inputs)
        self.assertEqual(r['phase_pair_count'], 320)
        self.assertEqual(r['phase_exposed_serial_sum_cycles'], 87800)
        for layer in range(40):
            rows = [n for n in r['phase_ledger'] if n['source'].startswith(f'L{layer}.')]
            self.assertEqual(len(rows), 8)
        self.assertFalse(r['headline_adoption'])
        self.assertGreater(r['authority_gap_us'], 4)

    def test_no_free_merge_gain(self):
        r = M.build(self.inputs)
        cases = r['current_source_DAG_cases_us']
        self.assertGreater(cases['candidate_bound_two_phase_sensitivity'], cases['candidate_bound_merged_pairs'])
        self.assertAlmostEqual(cases['candidate_bound_merged_pairs'], cases['unchanged'])
        self.assertGreater(r['historical_3809_exposed_sensitivity_us'], r['historical_3809_row']['T_us'])

    def test_zero_phase_not_allowed(self):
        with self.assertRaises(ValueError):
            M.phase_nodes(self.snapshot['nodes'], self.snapshot['config'], 1, {'a_proj':0,'gate_up':275})

    def test_dag_bad_dependency(self):
        with self.assertRaises(ValueError):
            M.solve({'n':dict(deps=['missing'],issue=1,depth=0,ctrl=0,stream=False)}, 'n')

    def test_qwen_matched_measurement(self):
        r = M.qwen_calibration(json.loads(self.inputs['qwen_measurement']))
        self.assertEqual(r['one256_cycles'], {'L0':3931,'L1':3930})
        self.assertEqual(r['saved_cycles'], {'L0':738,'L1':738})
        self.assertFalse(r['headline_adoption'])

    def test_qwen_wrong_payload(self):
        r = json.loads(self.inputs['qwen_measurement'])
        r['runs']['B']['x_sha256']['L0_die0_x'] = 'wrong'
        with self.assertRaises(ValueError):
            M.qwen_calibration(r)

    def test_qwen_wrong_binary(self):
        r = json.loads(self.inputs['qwen_measurement'])
        r['runs']['B']['binary_sha256'] = 'wrong'
        with self.assertRaises(ValueError):
            M.qwen_calibration(r)

    def test_changed_repetition_refuses(self):
        source = self.inputs['emitter'].decode().replace('range(m.k_exp)]', 'range(5)]')
        with self.assertRaises(ValueError):
            M.emitter_contract(source)

    def test_inconsistent_phase_receipt_refuses(self):
        inputs = dict(self.inputs)
        row = json.loads(inputs['phase_measurement'])
        row['ab']['expert_gate_up']['saved_cycles'] = 1
        inputs['phase_measurement'] = json.dumps(row).encode()
        with self.assertRaises(ValueError):
            M.build(inputs)

    def test_source_hash_refuses(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d/'bad').write_text('mutant')
            (d/'input_manifest.json').write_text(json.dumps({'inputs':{'x':{'archive':'bad','sha256':'0'*64}}}))
            with self.assertRaises(ValueError):
                M.load_inputs(d)

if __name__ == '__main__':
    unittest.main()
