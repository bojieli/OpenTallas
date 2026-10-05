import importlib.util,json,pathlib,unittest,math
P=pathlib.Path(__file__).resolve().parents[1];s=importlib.util.spec_from_file_location('f0',P/'tools/h4_hbm_bridge_f0_r3.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.outputs=m.outputs();cls.model=json.loads(cls.outputs['model.json'])
 def test_cold_directory_reads_exact_two_sectors_and_hit_has_positive_decode(self):
  payload=bytes(range(64));u=m.DescriptorLookup(payload,549.149,2,2)
  first=u.lookup(0,'a');second=u.lookup(0,'b');self.assertEqual(first['record'],payload);self.assertEqual(second['record'],payload);self.assertEqual(u.reads,2)
  self.assertEqual([r['bytes'] for r in first['events'][:2]],[32,32]);self.assertEqual([r['directory_offset'] for r in first['events'][:2]],[0,32]);self.assertEqual(len(second['events']),2)
  self.assertTrue(all(r['FAST_edges_PROVISIONAL']>0 for r in second['events']));self.assertIsNone(first['physical_reservation_receipt']);self.assertFalse(first['hardware_admitted'])
 def test_finite_cache_evict_then_real_miss_not_zero_or_wrong_record(self):
  u=m.DescriptorLookup(bytes([10])*64+bytes([20])*64,1,1,1,capacity=1)
  self.assertEqual(u.lookup(0,'a')['record'],bytes([10])*64);self.assertEqual(u.lookup(1,'b')['record'],bytes([20])*64);self.assertFalse(u.lookup(0,'c')['hit']);self.assertEqual(u.reads,6)
  with self.assertRaises(ValueError):u.lookup(2,'d')
 def test_positive_lookup_params_only(self):
  for n in [0,-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):m.DescriptorLookup(bytes(64),n,2,2)
  with self.assertRaises(ValueError):m.DescriptorLookup(bytes(64),1,0,2)
  with self.assertRaises(ValueError):m.DescriptorLookup(bytes(64),1,2,2,capacity=129)
 def test_exact_source_HBM_latency_and_decode_once(self):
  p=m.lookup_profile(m.data(m.inputs(),'ingress.json'));self.assertAlmostEqual(p['sector_read_ns_PROVISIONAL'],549.149);self.assertAlmostEqual(p['cold_lookup_ns_PROVISIONAL'],1098.298+4/1.2)
  d=self.model['positive21_stage_inventory']['directory_lookup'];self.assertAlmostEqual(d['additional_HBM_miss_ns_PROVISIONAL']+d['ns_PROVISIONAL'],p['cold_lookup_ns_PROVISIONAL']);self.assertIsNone(p['finite_contender_wait_upper_ns'])
 def test_fullshape_directory_counts_and_persistent_state_no_fabricated_SM(self):
  d=self.model['runtime_directory'];self.assertEqual(d['Qwen']['entries'],31232);self.assertEqual(d['DS']['entries'],290730)
  self.assertEqual(d['DS']['persistent_states'],4616);self.assertEqual(d['DS']['missing_home_SM'],4616)
  for name,r in d.items():self.assertEqual(r['cold_all_entries_reads32B'],2*r['entries']);self.assertEqual(r['HBM_reservation_bytes'],64*r['entries']);self.assertIsNone(r['physical_HBM_base'])
 def test_pipeline_replicas_metadata_bits_and_no_fifo_only_change(self):
  x=self.model;self.assertEqual(sum(x['active_route_fields']['request'].values()),313);self.assertEqual(sum(x['active_route_fields']['response'].values()),277)
  self.assertEqual(x['ports']['route_replicas_per_direction'],128);self.assertEqual(x['ports']['held_route_source_II_FAST_edges'],40);self.assertEqual(x['ports']['candidate_steady_pipeline_II'],1)
  self.assertEqual(x['pipeline']['total_pipeline_protected_bits'],7179264);self.assertEqual(x['ports']['source_common_ACK_events_per_RF_write'],1)
 def test_all21_real_KV_phases_join_positive21_service_terms(self):
  x=self.model;self.assertEqual(len(x['actual21_KV_phase_join']),21);self.assertEqual(set(x['positive21_stage_inventory']),set(m.EVENTS))
  for k,r in x['positive21_stage_inventory'].items():self.assertGreater(r['ns_PROVISIONAL'],0);self.assertIsNone(r['finite_wait_upper_ns'])
  self.assertGreater(x['positive21_stage_inventory']['refill']['additional_HBM_refill_ns_PROVISIONAL'],0)
  self.assertEqual(x['actual21_KV_phase_join']['sector_grant']['actual_occurrences'],39168)
 def test_once_only_calendar_occurrences_and_no_zero_nan_cost(self):
  row=dict(id='physical-source-ID',term='directory_HBM_read32B',duration_ns=549.149,origin='provisional_model');r=m.once([row,row]);self.assertEqual(r['occurrences'],1);self.assertEqual(r['serial_sum_ns_PROVISIONAL'],549.149)
  with self.assertRaises(ValueError):m.once([row,dict(row,term='different')])
  with self.assertRaises(ValueError):m.once([])
  with self.assertRaises(ValueError):m.once([dict(row,duration_ns=1e308),dict(row,id='second',duration_ns=1e308)])
  for n in [0,-1,float('nan'),float('inf')]:
   with self.assertRaises(ValueError):m.once([dict(row,duration_ns=n)])
 def test_complete_service_allocation_failure_not_small_slot_credit(self):
  for n,r in self.model['F0_allocations'].items():
   self.assertEqual(r['SMs'],32);self.assertEqual(r['candidate_cut_demand_per_SM_both_directions'],2896);self.assertFalse(r['new_F0_allocation_admitted']);self.assertGreater(r['additional_area_demand_with_min_clock_mm2'],38)
  self.assertEqual(self.model['F0_allocations']['DeepSeek']['existing_min_local_margin_tracks'],881)
 def test_runtime_directory_issuer_sixth_client_is_priced_not_free(self):
  x=self.model['directory_issuer'];self.assertEqual(x['source_PC_clients'],5);self.assertEqual(x['candidate_PC_clients'],6);self.assertEqual(x['new_live_home_tag_phase_counter_protected_bits'],9216);self.assertGreater(x['incremental_footprint_mm2_ASSUMED'],0);self.assertTrue(x['candidate_new_client_is_not_installed']);self.assertIsNone(x['actual_generic_client_to_PC_map'])
 def test_clock_complete_receiver_load_and_buffer_min_no_qualified_skew(self):
  c=self.model['clock'];self.assertEqual(c['complete_control_FF_bits_screen'],16519680+9216);self.assertGreater(c['buffer_instances_connectivity_min'],600000);self.assertGreater(c['buffer_connectivity_min_footprint_mm2'],.5);self.assertFalse(c['qualified_skew_slew_hold']);self.assertIsNone(c['new_clock_PG_OBS_via_cuts'])
 def test_authority_actual_contenders_and_waits_remain_unqualified(self):
  x=self.model;self.assertEqual(x['calendar']['source_actual_PC0_transactions'],738816);self.assertTrue(x['authority_R4']['selected_FETCH_already_paid']);self.assertFalse(x['engine_build_allowed']);self.assertIsNone(x['calendar']['whole_token_ns']);self.assertIsNone(x['calendar']['actual_event_interval_receipts'])
 def test_cold_exact_outputs(self):
  for n,v in self.outputs.items():self.assertEqual((m.BASE/n).read_bytes(),v)
if __name__=='__main__':unittest.main()
