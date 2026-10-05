"""Constructor-free source census and once-only composition gates."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('inventory',ROOT/'tools/hbm_fullsize_inventory_r1.py')
M=importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

class InventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt=M.compose()

    def counts(self,name):
        return {r['role']:r['count_per_die'] for r in self.receipt['models'][name]['inventory']}

    def test_required_fullsize_replicas(self):
        for name in ('Qwen','DeepSeek'):
            c=self.counts(name)
            self.assertEqual({k:c[k] for k in ('RF','scratch','L2','PHY')},dict(RF=4096,scratch=64,L2=256,PHY=4))

    def test_retained_xstore_staging_and_scale(self):
        q,d=self.counts('Qwen'),self.counts('DeepSeek')
        self.assertEqual((q['xstore'],q['staging'],q['row_scale']),(512,128,32))
        self.assertEqual((d['xstore'],d['staging'],d['row_scale']),(3168,160,0))

    def test_capture_contracts_are_not_substituted(self):
        self.assertEqual(self.counts('DeepSeek')['capture'],256)
        self.assertEqual(self.counts('Qwen')['capture'],0)
        for m in self.receipt['models'].values():
            self.assertFalse(m['capture']['contracts_equivalent'])
            self.assertFalse(m['capture']['accepted_demand_and_backpressure_proof'])

    def test_DS_staging_padding_and_summary_negative(self):
        d=self.receipt['models']['DeepSeek']['staging']
        self.assertEqual((d['useful_bytes_per_SM'],d['physical_bytes_per_SM'],d['context_summary_bytes_per_SM']),(139264,163840,131072))
        self.assertFalse(d['context_summary_matches_source'])

    def test_RF_area_is_contained_not_added(self):
        for m in self.receipt['models'].values():
            a=m['area']
            self.assertAlmostEqual(a['RF_raw_mm2'],15.93989922816)
            self.assertAlmostEqual(a['historical_RF_packed_mm2'],20.8812679888896)
            self.assertEqual(a['RF_packing_debit_added_again'],0)
            self.assertTrue(a['RF_already_contained_in_service_envelope'])
            self.assertEqual(M.sum_additive_area(a['charges']),a['selected_reserved_occupancy_mm2'])

    def test_area_duplicate_charge_refused(self):
        a=self.receipt['models']['Qwen']['area']['charges']
        with self.assertRaisesRegex(ValueError,'duplicate area'):M.sum_additive_area(a+[a[1]])

    def test_current_bridge_envelope_and_unknown_debit(self):
        for n,m in self.receipt['models'].items():
            b=m['current_bridge_composition']
            self.assertEqual(M.sum_additive_area(b['charges']),b['context_plus_reserved_slots_mm2'])
            self.assertAlmostEqual(b['context_plus_reserved_slots_mm2'],536.8439913267199 if n=='Qwen' else 561.1600554201599)
            self.assertIsNone(b['NC6_matched_old_debit_mm2'])
            self.assertIsNone(b['NC6_net_increment_mm2'])
            self.assertIsNone(b['exact_current_complete_area'])
            self.assertFalse(b['W6_subcomponent_added_again'])
            self.assertFalse(b['physical_admitted'])

    def test_current_protection_macro_alternative_not_adopted(self):
        for m in self.receipt['models'].values():
            p=m['protection']
            self.assertEqual(p['current_NC6_raw_state_bits'],611712)
            self.assertEqual(p['current_NC6_protected_state_bits'],1170432)
            self.assertEqual(p['W6_same_index_sidecar_macro_alternative_count'],128)
            self.assertFalse(p['W6_sidecar_macro_alternative_selected'])

    def test_area_containment_recharge_refused(self):
        a=copy.deepcopy(self.receipt['models']['Qwen']['area']['charges'])
        a[1]['additional_mm2']=20.8812679888896
        with self.assertRaisesRegex(ValueError,'contained cost'):M.sum_additive_area(a)

    def test_negative_area_credit_refused(self):
        with self.assertRaisesRegex(ValueError,'negative area'):M.sum_additive_area([dict(charge_id='refund',additional_mm2=-1,contained=False)])

    def test_duplicate_inventory_refused(self):
        a=self.receipt['models']['DeepSeek']['inventory']
        with self.assertRaisesRegex(ValueError,'duplicate inventory'):M.unique_inventory(a+[a[0]])

    def test_protection_scope_and_bits(self):
        for n,m in self.receipt['models'].items():
            p=m['protection']
            self.assertEqual(p['KV_constructive_state_bits_per_die'],81506)
            self.assertEqual(p['RF_visibility_state_bits_per_SM'],51)
            self.assertEqual(p['RF_visibility_payload_bits'],0)
            self.assertEqual(p['KV_source_operator_bound'],n=='Qwen')
            self.assertFalse(p['KV_installed'])
            self.assertIsNone(p['complete_protection_physical_area'])

    def test_PHY_interface_mismatch_preserved(self):
        for m in self.receipt['models'].values():
            p=m['shoreline']
            self.assertEqual(p['retained_PHY_interface_bits'],dict(address_bits=31,len_bits=5,beat_bits=4))
            self.assertEqual(p['selected_controller_required_bits'],dict(address_bits=31,len_bits=6,beat_bits=5))
            self.assertFalse(p['PHY_exact_interface_join'])
            self.assertIsNone(p['sustained_bandwidth_measurement'])

    def test_clock_subset_not_full_census(self):
        for n,m in self.receipt['models'].items():
            c=m['clock']
            self.assertEqual(c['gateway_service_macro_endpoints_per_SM'],130 if n=='Qwen' else 138)
            self.assertEqual(c['retained_matrix_memory_macro_endpoints_per_SM'],21 if n=='Qwen' else 104)
            self.assertEqual(c['retained_compute_macro_endpoints_per_SM'],64)
            self.assertFalse(c['gateway_clock_is_full_parent_load'])
            self.assertFalse(c['balanced_CTS_and_contextual_SSFF'])
            self.assertEqual((c['SS_setup_uncertainty_ps'],c['FF_hold_uncertainty_ps']),(60,25))

    def test_no_software_or_physical_admission_transfer(self):
        r=self.receipt
        self.assertEqual((r['RTL_elaborations'],r['PnR_jobs'],r['payload_reads']),(0,0,0))
        self.assertFalse(r['hardware_admitted'])
        for m in r['models'].values():
            self.assertIsNone(m['composition']['whole_token_ns'])
            self.assertFalse(m['composition']['build_GO'])
            self.assertTrue(all(not x['physical_qualified'] for x in m['inventory']))
        self.assertEqual(r['evidence_classification']['checkpoint_payload'],'NOT_READ_BY_THIS_RECEIPT')

    def test_source_drift_refused_before_composition(self):
        original=Path.read_bytes
        def read(path):
            b=original(path)
            return b+b'\n' if path==ROOT/'rtl/gpu/ot_gpu_sm_v.sv' else b
        with patch.object(Path,'read_bytes',read):
            with self.assertRaisesRegex(ValueError,'source drift'):M.compose()

    def test_unified_baseline_source_is_only_read(self):
        with patch.object(Path,'write_bytes',side_effect=AssertionError('mutation')),patch('subprocess.Popen',side_effect=AssertionError('process launch')):
            self.assertEqual(M.compose(),self.receipt)

    def test_cold_model_exact(self):
        self.assertEqual(M.encoded(M.compose()),(ROOT/M.DEST/'model-r1.json').read_bytes())

if __name__=='__main__':unittest.main()
