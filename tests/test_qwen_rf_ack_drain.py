import json
from pathlib import Path
import unittest
from tools.gpu_sys.qwen_rf_ack_drain_model import model
from tools.gpu_sys.canonical_qwen_rf_ack_drain import port_bindings,FILES
ROOT=Path(__file__).resolve().parents[1]
LEAF=ROOT/FILES[1];JOIN=ROOT/FILES[2]

class RFDrain(unittest.TestCase):
 def test_exact_cold_model(self):
  self.assertEqual(model(),json.loads((ROOT/'results/uarch/qwen_rf_ack_drain_20261003/model.json').read_text()))
 def test_paid64leaf_two_rank_no_duplicate_RF(self):
  m=model();self.assertEqual(m['organization']['leaves'],64);self.assertEqual(m['organization']['roots'],2)
  self.assertEqual(m['storage']['leaf_raw_bits'],479);self.assertEqual(m['storage']['leaf_protected_FF'],576)
  self.assertEqual(m['storage']['root_raw_bits'],151);self.assertEqual(m['storage']['root_protected_FF'],216)
  self.assertEqual(m['storage']['all_new_protected_FF'],64*576+2*216)
  self.assertEqual(m['storage']['new_SRAM_macros'],0);self.assertGreater(m['area']['full_two_rank_50pct_footprint_mm2_ASSUMED'],0)
 def test_no_latency_zero_or_hardware_clock_claim(self):
  m=model();self.assertFalse(m['clock']['SSFF']);self.assertIsNone(m['latency']['whole_token'])
  self.assertGreater(m['latency']['composed_min_root_request_to_cohort_reply_edges'],0)
  self.assertIn('NOT charged a second time',m['latency']['overlap'])
 def test_actual_W4_held_receipt_source_capacity(self):
  s=(ROOT/model()['source'][1]['path']).read_text()
  self.assertIn('reg write_pending;reg [54:0] accepted_identity;',s)
  self.assertIn('protected_ACK<=w4_encode(accepted_identity);ack_valid<=1;',s)
  self.assertIn('read_pending<=read_go;',s)
  self.assertIn('if(read_pending)',s)
 def test_actual_W6_all_reverse_before_retire(self):
  s=(ROOT/model()['source'][2]['path']).read_text()
  self.assertIn('next_raw[64]=1;',s);self.assertIn('next_raw[65]=1;',s);self.assertIn('next_raw[66]=1;',s)
  self.assertIn('phase==RETIRE && age_ok && raw[67]',s)
  l=LEAF.read_text();self.assertIn('!(&raw[391:387])',l);self.assertIn('w6_retire_owner55!=raw[299:245]',l)
 def test_current_fault_observes_raw_ACK_not_masked_accept(self):
  s=LEAF.read_text();cone=s.split('wire current_fault=',1)[1].split(';',1)[0]
  self.assertNotIn('accept',cone);self.assertNotIn('permit',cone)
  self.assertIn('rf_ack_valid&&(!wr_live',s)
 def test_same_edge_source_admission_violation_cannot_reply_empty(self):
  s=LEAF.read_text();self.assertIn('&&!new_matching_accept;',s)
  self.assertIn('if(rf_write_accept&&!wr_permit)n[478]=1;',s)
  self.assertIn('if(rf_read_accept&&!rd_permit)n[478]=1;',s)
  self.assertIn('if(w6_request_accept&&!w6_permit)n[478]=1;',s)
 def test_matching_key_stop_closes_new_but_not_old_reverse(self):
  s=LEAF.read_text();self.assertIn('wire stop=draining||drain_req_valid||drain_hold;',s)
  for stream in ('wr','rd','w6'):
   self.assertIn('!(stop&&'+stream+'_KV_related&&'+stream+'_key==stop_key)',s)
  self.assertIn('if(w6_CDC_accept)',s);self.assertIn('if(w6_retire_accept)',s)
 def test_local_W6_RF_bit_not_own_retirement(self):
  s=LEAF.read_text();cone=s.split('assign w6_local_RF_empty=',1)[1].split(';',1)[0]
  self.assertIn('!wr_live&&!rd_live',cone);self.assertIn('raw[387]',cone)
  self.assertNotIn('retire',cone);self.assertNotIn('responded',cone)
 def test_warm_reset_retains_receipts_and_hold(self):
  s=LEAF.read_text();self.assertIn('(!rst_n&&(wr_live||rd_live||w6_live||draining))',s)
  self.assertIn('assign drain_retained=draining;',s)
  self.assertNotIn('if(!rst_n)begin',s)
  self.assertIn('if(!por_n)',s)
 def test_rank_join_32_real_replies_not_allones(self):
  s=JOIN.read_text();self.assertIn('for(g=0;g<32;g=g+1)',s)
  self.assertIn('leaf_rsp_tuple[g*84+:84]!={dkey,did}',s)
  self.assertIn('if(leaf_rsp_valid[j]&&leaf_rsp_ready[j])n[116+j]=1;',s)
  self.assertIn('!responded&&(&seen)',s);self.assertIn('assign leaf_hold={32{active}};',s)
 def test_portmap_actual_handshakes_no_software_ownership(self):
  b=port_bindings();self.assertEqual(b['cohort_index'],4)
  for stream in (b['actual_W4'],b['actual_W6']):
   for name,expression in stream.items():
    if name.endswith('_accept'):self.assertIn('&&',expression)
  self.assertIn('actual retained reader release',b['parent_hold']['Dewey_connected'])
  self.assertIn('excludes W6 own row',b['W6_local_RF_bit'])

class BootScope(unittest.TestCase):
 def test_no_owner_boot_requires_actual_W6_reset_scope(self):
  s=LEAF.read_text()
  self.assertIn('!w6_local_drain_has_owner&&w6_local_drain_reset_scope&&!w6_live',s)
  self.assertIn('w6_local_drain_owner55==raw[299:245]',s)
  b=port_bindings()['actual_W6']
  self.assertEqual(b['w6_local_drain_has_owner'],'fence.drain_req_has_owner')
  self.assertEqual(b['w6_local_drain_reset_scope'],'fence.drain_req_reset_scope')

if __name__=='__main__':unittest.main()
