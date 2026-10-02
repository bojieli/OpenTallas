import importlib.util,json,unittest
from pathlib import Path
P=Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('noECC',P/'tools/dsrom_ROM_noECC_candidate.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class NoECC(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.r=m.build()
 def test_only_same_candidate(self):self.assertEqual(self.r['candidate'],'DS4096-TP4-S58-PAR2-NP2048');self.assertEqual(self.r['physical']['stages'],58);self.assertEqual(self.r['physical']['TP'],4)
 def test_only_ROM_protection_removed(self):
  for k in ('SRAM_protection','HBM_protection','link_protection','transaction_identity_generation_nonce_and_fault_checks'):self.assertTrue(self.r['scope'][k])
  for k in ('ROM_weight_ECC','ROM_configuration_ECC','ROM_sidecar_mirror_ECC'):self.assertFalse(self.r['scope'][k])
 def test_no_macro_credit(self):
  p=self.r['physical'];self.assertEqual(p['original_and_mirror_macros_removed'],0);self.assertEqual(p['field_macros_per_shard'],8192);self.assertEqual(p['cfg_macros_per_shard'],14336);self.assertEqual(p['ROM_macro_body_area_credit_mm2'],0);self.assertTrue(p['no_repack_or_new_weights_in_freed_ECC_roles'])
 def test_area_union(self):
  a=self.r['area'];self.assertAlmostEqual(a['new_conservative_per_shard_screen_mm2'],a['underlying_field_cfg_return_fixed_service_routes_clockPG_residual_retained_mm2']+sum(a['retained_common_main_terms_mm2'].values()));self.assertAlmostEqual(a['removed_unique_ECC_total_mm2'],5.80433952384)
 def test_common_state_not_deleted(self):
  a=self.r['area']['retained_common_main_terms_mm2'];self.assertGreater(a['main_request_identity_capture_state'],0);self.assertGreater(a['main_data_selection_proxy'],0);self.assertGreater(a['old_area_rounding_policy'],0)
 def test_payload_and_physical_width(self):
  p=self.r['physical'];self.assertEqual(p['main_macro_carrier_bits'],274);self.assertEqual(p['paired_conservative_held_carrier_bits'],548);self.assertEqual(p['native_source_paired_capture_bits'],548);self.assertEqual(p['paired_main_arithmetic_payload_bits'],544);self.assertEqual(p['new_protected_checker_input_bits'],0);self.assertTrue(p['golden_payload_address_and_order_unchanged'])
 def test_real_source_edges(self):
  t=m.source_timeline(20);self.assertEqual(t['source_capture_postNBA'],22);self.assertEqual(t['original_arithmetic_preedge'],23);self.assertEqual(t['source_sampling_delay_added'],0)
 def test_bad_edges(self):
  for x in (-1,None,True):
   with self.assertRaises(ValueError):m.source_timeline(x)
 def test_leases_not_free(self):
  c=self.r['conditional_held_lease'];self.assertEqual(c['conditional_peak_if_old_perread_lease_ACK_protocol_retained'],320);self.assertEqual(c['unchanged_128_lease_capacity'],128);self.assertFalse(c['feed_is_actual_fullphase_accept_trace']);self.assertTrue(c['extra_slots_not_selected_or_added_to_screen'])
 def test_Qwen_failure_and_control_retained(self):
  q=self.r['Qwen'];self.assertTrue(q['SSFF_failure_still_requires_bank_control_reset_arrival_repair']);self.assertEqual(q['own_control_area_credit'],0);self.assertEqual(q['loaded_control_failure_preserved'],'f28f30496d5489a76b90c3bc45fc479e4fcc5881')
 def test_no_admission(self):
  a=self.r['admitted'];self.assertTrue(a['model_reprice']);self.assertTrue(all(not v for k,v in a.items() if k!='model_reprice'));self.assertEqual(self.r['new_fleet_jobs'],0)
 def test_topk_store_counted_once(self):
  x=self.r['full_topk_slot'];self.assertAlmostEqual(x['already_inherited_store_mm2'],.3075936768);self.assertAlmostEqual(x['additional_state_only_debit_once_mm2'],.0617719608);self.assertAlmostEqual(x['same_candidate_screen_with_topk_state_only_mm2'],727.2228976728057)
 def test_complete_filter_gate(self):
  x=self.r['full_topk_slot'];self.assertTrue(x['balanced_filter_quota_prefix_compaction_logic_state_stages_unpriced']);self.assertFalse(x['full_slot_G0']['engine_RTL_admitted']);self.assertTrue(x['adjacent_common_controller_and_corridor_displacement_not_free'])
 def test_configuration_ECC_optional(self):
  self.assertEqual(self.r['scope']['ROM_configuration_ECC_status'],'optional/historical');self.assertIn('semantic fault',self.r['configuration_scope']);self.assertTrue(self.r['physical']['cfg72bit_carrier_retained_48bit_payload_correctness_semantic_checks_required'])
 def test_no_unproven_instantiated_credit(self):
  a=self.r['area'];self.assertEqual(a['actual_instantiated_ROM_ECC_area_credit_mm2'],0);self.assertFalse(a['actual_instantiated_ROM_ECC_area_receipt_available']);self.assertTrue(a['removed_terms_are_source_priced_proposal_reservations_not_instantiated_area'])
 def test_no_speculative_cfg_credit(self):
  self.assertEqual(self.r['physical']['configuration_ECC_area_credit_mm2'],0);self.assertEqual(self.r['area']['configuration_ROM_ECC_instantiated_cost_not_bound_credit_mm2'],0)
 def test_byte_model(self):self.assertEqual(self.r,json.loads((m.OUT/'model-r6.json').read_text()))
if __name__=='__main__':unittest.main()
