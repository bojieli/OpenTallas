import pathlib,unittest,hashlib,json
R=pathlib.Path(__file__).resolve().parents[1]
class Source(unittest.TestCase):
 def test_original_full_bodies_byteidentical(self):
  for mod in ('ot_gpu_rf_service','ot_gpu_full_sm_service'):
   original=(R/'rtl/gpu'/f'{mod}.sv').read_text();successor=(R/'rtl/gpu_w4_euclid_20261003'/f'{mod}.sv').read_text()
   self.assertTrue(successor.endswith(original.replace('module '+mod+' ','module '+mod+'_W4_original ')))
 def test_actual_pipeline_and_identity(self):
  s=(R/'rtl/gpu_w4_euclid_20261003/ot_gpu_rf_service.sv').read_text();self.assertIn('accepted_identity<={wr_owner,wr_addr}',s);self.assertIn('if(write_pending) begin protected_ACK<=w4_encode(accepted_identity);ack_valid<=1;',s);self.assertEqual(s.count('.w_ce_in(write_go && wr_addr[8:7]==p)'),4)
 def test_source_SIMD_capture(self):
  s=(R/'rtl/gpu_w4_euclid_20261003/ot_gpu_full_sm_service.sv').read_text();self.assertIn('if(sg) begin simd_identity_q<=w4_encode({simd_owner,simd_dst});',s);self.assertIn('.wr_owner(idle?host_owner:simd_identity[54:9])',s);self.assertIn('rf_ack_slot==dst_q',s)
 def test_no_connector_claim(self):
  x=json.loads((R/'results/uarch/Euclid_W4_RFACK_identity_contract_20261003/connector-r4/prebuild-contract-r4.json').read_text());self.assertFalse(x['whole_connector_build_admitted']);self.assertFalse(x['real_C0_KV_caller_proven']);self.assertIsNone(x['positive_global_drain_wait_cycles'])
if __name__=='__main__':unittest.main()
