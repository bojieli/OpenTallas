import ast,gzip,importlib.util,json,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reuse',ROOT/'tools/dsrom_PAR2_padding_parity_binding.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class PaddingParityBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.model,cls.roles,cls.obs,cls.incidence,cls.cuts=m.build()
 def test_all58_maps_use_only_original_q_padding(self):
  field=m.load('provider_readback.json')['compiled_field'];available=set(field['padding_site_IDs'])-set(field['BF_DUAL_site_IDs']);active=set(field['weight_active_site_IDs'])
  for p in m.load('mirror.jsonl.gz'):
   self.assertEqual(len(p['mirror_pairs']),103);self.assertTrue(set(p['mirror_pairs'])<=available);self.assertTrue(set(p['original_pairs'])<=active);self.assertFalse(set(p['mirror_pairs'])&active)
  self.assertEqual(self.model['ownership']['remaining_shard1_padding'],281)
 def test_exact_existing_instances_not_new_placement(self):
  self.assertEqual(len(self.roles),412);self.assertEqual(len({r['name'] for r in self.roles}),412)
  tool=m.module('current',ROOT/'tools/dsrom_PAR2_shard_physical_binding.py');parent,macros,*_=tool.build(1);byname={r['name']:r for r in macros}
  for r in self.roles:self.assertEqual(r['bbox_DBU'],byname[r['name']]['bbox_DBU']);self.assertFalse(r['new_macro_instance'])
  self.assertEqual(self.model['storage']['incremental_macro_instances'],0)
 def test_no_duplicate_body_or_halo_debit(self):
  s=self.model['storage'];a=self.model['area'];self.assertEqual(s['incremental_macro_body_mm2'],0);self.assertEqual(s['incremental_macro_halo_mm2'],0)
  self.assertGreater(a['total_incremental_allowance_mm2'],5.9);self.assertLess(a['total_incremental_allowance_mm2'],6.0);self.assertEqual(a['sidecar_leaf_decoder_replicas'],412);self.assertEqual(a['main_codeword_decoder_replicas'],256);self.assertAlmostEqual(a['incremental_logic_allowance_mm2'],sum(a['named_logic_allowance_mm2'].values()));self.assertAlmostEqual(a['prior_separate_storage_body_halo_debit_removed_mm2'],4.0520549376)
  self.assertAlmostEqual(a['with_existing_clearances_screen_mm2']+a['remaining_for_unpriced_physical_endpoints_exclusions_mm2'],858)
  self.assertTrue(a['inherited418_residual47_and_complete_q_padding_frame_charges_retained'])
 def test_source_function_all_protected_word_boundaries(self):
  tree=ast.parse((m.OUT/'inputs/mirror_source.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='local_sidecar_address');ns={'B':types.SimpleNamespace(site=lambda p:{'source_site':p})};exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned_r3','exec'),ns)
  checks=0
  for p in m.load('mirror.jsonl.gz'):
   for i in range(103):
    start=i*4194304;stop=min(p['bits'],start+4194304)
    if start>=stop:continue
    for bit in (start,stop-1):
     r=ns['local_sidecar_address'](p,bit,1);self.assertEqual(m.local_address(p,bit),(r['source_site'],r['mb'],r['parity'],r['physical_row'],r['data_bit']));checks+=1
  self.assertEqual(checks,8448)
 def test_protected256_plus10_contract_not272_weight_alias(self):
  s=self.model['storage'];self.assertEqual(s['protected_payload_data_bits'],256);self.assertEqual(s['protected_check_bits'],10);self.assertEqual(s['physical_word_bits'],274)
  with self.assertRaises(ValueError):m.local_address(m.load('mirror.jsonl.gz')[0],-1)
 def test_unchanged_bank_conflicts_and_finite_gate(self):
  s=self.model['source_service'];self.assertEqual(s['retained_first_address_bank_conflict_read_rounds'],64);self.assertEqual(s['conditional_max_read_rounds_per128seat_batch'],128);self.assertFalse(s['no_loss_original_deadline_proof']);self.assertTrue(s['current_source_accept_ready_sidecar_and_decoder_absent'])
 def test_routes_are_incidence_not_wirelength_or_capacity(self):
  r=self.model['routing'];self.assertGreater(r['pin_to_consumer_frame_center_max_Manhattan_um'],20000);self.assertEqual(r['representative_vertical_reply_cut_peak']['reply_bits_if_fully_parallel'],528);self.assertFalse(r['clock_PG_via_pin_escape_and_admissible_cut_capacity_bound']);self.assertEqual(r['collector_band_capacity_credit_taken'],0)
 def test_original_macro_clock_shapes_no_free_logic_clock(self):
  g=self.model['geometry'];self.assertEqual(g['additional_macro_clock_pin_count'],0);self.assertTrue(g['additional_logic_clock_cap_and_toggling_PG_unbound']);self.assertFalse(g['actual_PG_via_CTS_exclusions_qualified']);self.assertFalse(self.model['physical_GO'])
 def test_prior_variant_preserved(self):
  self.assertEqual(self.model['preserved_prior_variant']['sha256'],m.sha(m.PRIOR/'local_parity_model.json'));self.assertEqual(self.model['new_RTL_compile_PR_jobs'],0)
if __name__=='__main__':unittest.main()
