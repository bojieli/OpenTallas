import importlib.util
import json
import math
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('c0_model',ROOT/'tools/h4_hbm_c0_connected_bridge_model.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)
class ModelTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.m=M.model()
 def test_real_source_homes(self):
  gate=self.m['source_operand_plan']['source_gate_home']
  self.assertEqual((gate['storage_rank'],gate['storage_SM'],gate['RFslot9']),(0,0,38))
  self.assertEqual([v['RF_vectors'] for v in self.m['source_operand_plan']['transient_enrollment']],[[17],[18],[19]])
 def test_native_leaf_order(self):
  self.assertEqual(self.m['ordered_native_steps'],[{'dst':'out','op':'NEG','src':['x']},{'dst':'ex','op':'FMAX','src':['x','f32(-87)']}])
  self.assertEqual([a['action'] for a in self.m['source_operand_plan']['ordered_producer_actions']],['read_source_home','BITCAST_U','broadcast_U32','XOR','BITCAST_F','broadcast_F32','FMAX'])
 def test_no_fake_HBM_reads(self):self.assertEqual(self.m['state']['new_HBM_transactions'],0);self.assertFalse(self.m['W2']['selected_on_this_RF_path'])
 def test_b846_actual_new_price(self):
  self.assertEqual(self.m['W2']['HBM_candidate_protected_bits_perPC'],13608)
  self.assertEqual(self.m['W2']['HBM_candidate_II'],8)
  self.assertEqual(self.m['W2']['HBM_candidate_read_bytes_per_edge_upper'],4)
  self.assertIsNone(self.m['W2']['old_F0_matched_replacement_debit'])
  self.assertEqual(self.m['W2']['minimum_clean_request_read_write_edges'],[8,8,9])
  self.assertEqual(self.m['W2']['earliest_read_write_edges'],[11,12])
  self.assertIsNone(self.m['W2']['repair_contention_extra_edges'])
 def test_stage_provider_transaction_count(self):
  self.assertEqual(self.m['ports']['RF_read_count'],3);self.assertEqual(self.m['ports']['RF_write_count'],5)
  self.assertEqual(self.m['ports']['physical_mirror_write_bits'],40960)
 def test_retained_metadata_not_tag_truncated(self):self.assertEqual(self.m['native_identity_bits'],128);self.assertEqual(self.m['RF_identity_bits'],55)
 def test_positive_costs(self):self.assertTrue(all(x>0 for x in self.m['calendar']['event_edges'].values()))
 def test_no_unknown_zero(self):self.assertIsNone(self.m['whole_token_latency_ns']);self.assertFalse(self.m['physical_build_admitted']);self.assertIsNone(self.m['cuts']['selected_channel_capacity'])
 def test_conditional_wait_sensitivity(self):self.assertGreater(M.model(16)['calendar']['duration_ns'],M.model(1)['calendar']['duration_ns'])
 def test_period_sensitivity(self):self.assertAlmostEqual(M.model(4,1)['calendar']['duration_ns']/self.m['calendar']['duration_ns'],1.2)
 def test_reject_zero_negative_or_nonfinite_cost(self):
  for x in (0,-1,True,1.5):
   with self.subTest(wait=x),self.assertRaises(ValueError):M.model(x)
  for x in (0,-1,float('inf'),float('nan')):
   with self.subTest(period=x),self.assertRaises(ValueError):M.model(4,x)
 def test_replica32_full_charge(self):self.assertEqual(self.m['area']['full32SM_controller_footprint_mm2_ASSUMED'],32*self.m['area']['controller_footprint_mm2_50pct_ASSUMED'])
 def test_no_new_RF_macro_doublecount(self):self.assertEqual(self.m['state']['new_RF_macros'],0);self.assertTrue(self.m['area']['W6_replaces_existing_rows_not_added_again'])
 def test_mutable_storage_count_matches_literal(self):
  self.assertEqual(self.m['state']['control_protected_bits'],288)
  self.assertEqual(self.m['state']['vector_protected_bits'],9216)
  self.assertEqual(self.m['state']['mutable_codec_words'],260)
 def test_rounding_and_stall_limits_not_measured(self):self.assertIn('NOT qualified',self.m['calendar']['clock_scope']);self.assertIsNone(self.m['calendar']['finite_wholeprogram_contender_bound'])
 def test_model_record_replay(self):
  record=json.loads((M.BASE/'model.json').read_text());self.assertEqual(record['model'],self.m)
 def test_input_mutant_manifest_refuses(self):
  original=M.INPUT_SHA;M.inputs.cache_clear()
  try:
   M.INPUT_SHA='0'*64
   with self.assertRaisesRegex(ValueError,'manifest identity'):M.inputs()
  finally:M.INPUT_SHA=original;M.inputs.cache_clear()
 def test_source_consumer_default_off(self):
  with self.assertRaisesRegex(ValueError,'default off'):M.emit_source(M.source_plan(1,1))
 def test_source_consumer_native64_kept(self):
  plan=M.source_plan(2**60+7,2**59+3);packet=M.emit_source(plan,enabled=True)
  self.assertEqual(packet['native_command']['owner_tag'],2**60+7)
  self.assertEqual(packet['native_command']['generation'],2**59+3)
  self.assertEqual(packet['HBM_addresses'],[]);self.assertIsNone(packet['W2_parent55'])
  self.assertIsNone(packet['issuer_owner46'])
 def test_source_consumer_rejects_stale_home_expression_or_lease(self):
  import copy
  base=M.source_plan(9,7)
  for where,key,value in [('native_command','opcode','FADD'),('source_gate_home','RFslot9',39),('source_gate_home','lease','stale')]:
   plan=copy.deepcopy(base);plan[where][key]=value
   with self.assertRaisesRegex(ValueError,'exact Ampere'):M.emit_source(plan,enabled=True)
  plan=copy.deepcopy(base);plan['ordered_producer_actions'][2]['bits']=0
  with self.assertRaises(ValueError):M.emit_source(plan,enabled=True)
 def test_source_consumer_rejects_invented_W2_parent(self):
  p=M.source_plan(1,1);p['parent55']=123
  with self.assertRaises(ValueError):M.emit_source(p,enabled=True)
if __name__=='__main__':unittest.main()
