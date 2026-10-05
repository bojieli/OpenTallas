import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reconcile',ROOT/'tools/hbm_w2_w6_inventory_reconciliation_r1.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)

class ReconciliationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.r=M.compose()

    def test_selected_W6_71_144_and_32SM(self):
        w=self.r['W6']
        self.assertEqual((w['raw_bits_per_SM'],w['protected_bits_per_SM'],w['raw_bits_32SM'],w['protected_bits_32SM']),(71,144,2272,4608))
        self.assertEqual(sum(w['raw_fields'].values()),71)
        self.assertEqual(w['generation_bits_charged_separately'],0)

    def test_W6_complete_proxy_once(self):
        w=self.r['W6']
        self.assertAlmostEqual(w['logic_um2_per_SM'],938.1904)
        self.assertAlmostEqual(w['slot_mm2_32SM'],.0600441856)
        self.assertEqual(w['identity_match_loads_per_bit'],7)
        self.assertEqual(w['clock_reset_loads_32SM'],4608)
        for m in self.r['models'].values():
            d=m['W6_once_only_replacement']
            self.assertAlmostEqual(d['old_component_mm2'],.0547705856)
            self.assertAlmostEqual(d['delta_mm2'],.0052736)
            self.assertFalse(d['exact_inclusion_in_bridge_upper_confirmed'])
            self.assertFalse(d['bridge_slot_envelope_added_again'])

    def test_legacy_51_not_current_W6(self):
        l=self.r['legacy_RF_fence']
        self.assertEqual(l['raw_bits_per_SM'],51)
        self.assertTrue(l['not_selected_W6'])
        self.assertFalse(l['legacy_cost_subtracted_as_W6'])

    def test_NC6_actual_sequential_source_sections(self):
        w=self.r['W2']
        self.assertEqual(w['source_census']['section_bits'],dict(table=3744,counters_RR_fault=34,request_holder=335,read_query=297,read_delivery=300,write_query=41,write_selection=30))
        self.assertEqual((w['raw_bits_per_PC'],w['raw_bits_128PC']),(4781,611968))
        self.assertEqual(sum(w['source_census']['fields'].values()),4781)

    def test_NC6_guard_padding_and_area(self):
        w=self.r['W2']
        self.assertEqual((w['protected_bits_per_PC'],w['protected_bits_128PC']),(9144,1170432))
        self.assertEqual(w['capture_invalid_extra_raw_bits_128PC'],256)
        self.assertTrue(w['invalid_bits_use_existing_query_padding'])
        self.assertAlmostEqual(w['gross_slot_mm2_128PC'],6.63848068608)
        self.assertFalse(w['protected_storage_implemented'])

    def test_no_blind_W2_gross_addition(self):
        for m in self.r['models'].values():
            w=m['W2_once_only']
            self.assertIsNone(w['matched_F0_old_W2_debit_mm2'])
            self.assertIsNone(w['net_increment_mm2'])
            self.assertAlmostEqual(w['guard_refinement_gross_delta_mm2'],.0126531072)
            self.assertIsNone(m['exact_current_composed_area_mm2'])
            self.assertTrue(w['no_blind_gross_addition'])

    def test_exact_replacement_not_full_addition(self):
        self.assertEqual(M.replace_component(10,2,3),11)
        with self.assertRaisesRegex(ValueError,'invalid replacement'):M.replace_component(10,11,3)
        with self.assertRaisesRegex(ValueError,'invalid replacement'):M.replace_component(10,-2,3)

    def test_unpriced_new_sequential_state_refused(self):
        t=(ROOT/M.W2_RTL).read_text()
        t=t.replace('reg hv,hw;', 'reg hv,hw; reg hidden;').replace('fault<=0;', 'fault<=0;hidden<=0;',1)
        with self.assertRaisesRegex(ValueError,'sequential source name'):M.nc6_state_census(t,self.r['W2']['geometry'])

    def test_incorrect_source_parameter_changes_count(self):
        p=copy.deepcopy(self.r['W2']['geometry']);p['NC']=5
        c=M.nc6_state_census((ROOT/M.W2_RTL).read_text(),p)
        self.assertNotEqual(c['raw_bits'],4781)

    def test_no_eval_of_source_dimension_calls(self):
        with self.assertRaisesRegex(ValueError,'unsupported source'):M.integer('open(1)',{})

    def test_mutated_selected_source_refused(self):
        original=Path.read_bytes
        def read(p):
            b=original(p)
            return b+b'\n' if p==ROOT/M.W6_RTL else b
        with patch.object(Path,'read_bytes',read):
            with self.assertRaisesRegex(ValueError,'source drift'):M.compose()

    def test_source_scopes_and_positive_wait_unknown(self):
        self.assertFalse(self.r['historical_inventory_origin']['current_implementation_complete'])
        self.assertIsNone(self.r['W6']['finite_maximum_edges'])
        self.assertFalse(self.r['W6']['producer_of_alldrain_live_installed'])
        for m in self.r['models'].values():
            self.assertIsNone(m['whole_token_ns'])
            self.assertFalse(m['build_GO'])
            self.assertFalse(m['source_production_drain_or_reset_bound'])

    def test_constructor_free_and_readonly(self):
        with patch('subprocess.Popen',side_effect=AssertionError('launch')),patch.object(Path,'write_bytes',side_effect=AssertionError('mutation')):
            self.assertEqual(M.compose(),self.r)
        self.assertEqual([self.r[k] for k in ('payload_reads','constructors','RTL_elaborations','PnR_jobs','numerical_runs')],[0]*5)

    def test_cold_model_exact(self):
        self.assertEqual(M.encoded(M.compose()),(ROOT/M.HOME/'model-r1.json').read_bytes())

if __name__=='__main__':unittest.main()
