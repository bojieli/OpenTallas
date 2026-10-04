import hashlib,json,unittest
from pathlib import Path
D=Path(__file__).resolve().parent;ROOT=D.parents[3]

class InstalledSourceTests(unittest.TestCase):
 def test_issuer_range_and_frame_boundary(self):
  s=(D/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
  self.assertIn('ot_gpu_qwen_full_issuer_r2 #',s)
  self.assertIn('.inputs_bound_mask(issuer_inputs_bound_mask)',s)
  self.assertIn('.rf_range_ack_page_mask(issuer_rf_range_ack_page_mask)',s)
  self.assertIn('.frame_retire_valid(issuer_frame_retire_valid)',s)
  self.assertNotIn('.rf_ack_valid(issuer_rf_ack_valid)',s)
  self.assertNotIn('source_retire',s)
 def test_guarded_SM_real_accepted_and_stalled_paths(self):
  s=(D.parent/'guarded_sm/ot_gpu_full_sm_service_guarded.sv').read_text()
  for term in ('rd_permit && ctx_clean','wr_permit && ctx_clean','rf_rsp_allow && ctx_clean','rf_ack_allow && ctx_clean', 'simd_context_permit && ctx_clean','READ: if(rr && rd_permit','OPERATE: if(rv && rf_rsp_allow','WRITE: if(wr && wr_permit'):
   self.assertIn(term,s)
  self.assertIn('simd_key,simd_source_identity',s)
  self.assertIn('actual',s)
  self.assertIn('if(!OPT_CONTEXT)',s)
  top=(D/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
  self.assertIn('.OPT_CONTEXT(ENABLE),.INSTANCE_ID(i)',top)
  self.assertIn('.simd_context_accept(sm_simd_context_accept[i])',top)
  self.assertIn('.wr_identity(sm_wr_context_identity[i*64 +: 64])',top)
  self.assertIn('.rf_ack_allow(rfdrain_rf_ack_allow[i])',top)
 def test_STATE_command_symmetric_and_observer_ready_driven(self):
  s=(D/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
  self.assertIn('.command_valid(state_rpc_tap_command_valid && (!sector_grant_live || state_route_shared))',s)
  self.assertIn('assign state_command_ready=raw_state_command_ready && (!sector_grant_live || state_route_shared);',s)
  self.assertIn('.observe_valid(state_observe_valid)',s)
  self.assertIn('.observe_ready(kv_observe_ready)',s)
  self.assertIn('assign state_observe_ready=kv_observe_ready;',s)
  self.assertNotIn('assign kv_observe_ready=',s)
  self.assertIn('.ACK_ready(kv_ACK_ready)',s)
  self.assertIn('state_reply_owner[45:39]',s)
  self.assertIn('state_req_permit & (state_route_shared ? sector_req_permit',s)
  self.assertIn('state_capture_permit & (state_route_shared ? sector_capture_permit',s)
 def test_actual_all64RF_cohort4_and_tuple_source(self):
  b=json.loads((D/'ports.json').read_text());s=(D/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
  self.assertEqual(b['inventory']['RF_cohort_leaf_count'],64)
  self.assertEqual(b['inventory']['RF_rank_join_count'],2)
  self.assertIn('rfcohort_req_ready=&rfjoin_drain_req_ready',s)
  self.assertIn('.drain_req_valid(kv_cohort_req_valid[4] && rfcohort_req_ready)',s)
  self.assertIn('.drain_hold(kv_drain_retained)',s)
  self.assertIn('rfdrain_drain_rsp_key[q*20+:20],rfdrain_drain_rsp_identity[q*64+:64]',s)
  self.assertEqual(b['overridden_external_input_masks']['kv_cohort_rsp_valid'],25)
  self.assertFalse(b['token_qualified']);self.assertFalse(b['physical_qualified'])

 def test_STATE_whole_rpc_cohort_and_sharedgrant_route(self):
  s=(D/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
  for term in ('ot_gpu_qwen_kv_state_rpc_join #','ot_gpu_qwen_kv_local_cohorts_terminal_ready #',
   '.state_root_accept(state_rpc_root_accept)', '.state_root_retire(state_rpc_root_retire)',
   '.root_admit(local_state_root_admit)', '.root_retire_ready(local_state_root_retire_ready)',
   '.tap_reply_valid(state_reply_valid)', '.reply_ready(state_rpc_tap_reply_ready)',
   'sector_grant_identity[136]==','sector_grant_identity[79:46]==','sector_grant_identity[45:0]==',
   'sector_reverse_valid && (!state_bus_owned || (state_route_shared && state_reverse_ready))',
   'sector_reverse_valid && state_bus_owned && (!state_route_shared || payload_reverse_ready)',
   'state_reverse_ready && (!state_route_shared || payload_reverse_ready)',
   '.shared_service_ready(sm_scratch_ready)', '.shared_service_done(sm_scratch_done)'):
   self.assertIn(term,s)
  self.assertNotIn('.command_valid(state_command_valid && !sector_grant_live)',s)
  self.assertNotIn('.root_retire(state_reply_valid)',s)
  self.assertNotIn('sector_capture_valid &',s)
  book=json.loads((D/'ports.json').read_text())
  self.assertEqual(book['installed_cohorts'],{'RF_ACK':4,'local_stage':0,'metadata_RPC':3})
  for name in ('stage_root_accept','stage_root_retire','stage_root_owner','stage_root_retire_owner'):
   self.assertEqual(book['pins']['local_'+name]['direction'],'input')
  api=(ROOT/'tools/gpu_sys/canonical_qwen_ranked_simulator.py').read_text()
  self.assertIn("for kind in ('kv_state_read','kv_state_write'):handlers[kind]=state.handlers[kind]",api)
  rpc=(ROOT/'tools/gpu_sys/canonical_qwen_state_rpc_join.py').read_bytes()
  self.assertEqual(hashlib.sha256(rpc).hexdigest(),book['factory_source_sha256']['tools/gpu_sys/canonical_qwen_state_rpc_join.py'])

if __name__=='__main__':unittest.main()
