import unittest,sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import h4_hbm_pc40_physical_ack_r3 as M
class ACKTests(unittest.TestCase):
 def new(self,slot=17):
  r=M.ACKReference();r.accept_root((1<<45)|(1<<35)|3);r.write(slot);return r
 def test_all_actual_source_writes(self):
  r=M.ACKReference();r.accept_root((1<<45)|(1<<35)|3)
  for slot in [17,18,17,18,19]:
   r.write(slot);self.assertFalse(r.ack(r.owner,slot,slot));self.assertTrue(r.pending)
   self.assertTrue(r.ack(r.owner,slot,slot));self.assertFalse(r.pending)
 def test_no_zero_edge_ACK(self):
  r=self.new();self.assertFalse(r.ack(r.owner,17,17));self.assertTrue(r.checked)
 def test_current_ACK_phase_address19_not_context(self):
  r=self.new();self.assertFalse(r.ack(r.owner,19,17));self.assertTrue(r.fault);self.assertTrue(r.pending)
 def test_owner_PC7(self):self.owner_mutant(45)
 def test_owner_client3(self):self.owner_mutant(36)
 def test_owner_originaltag32_high(self):self.owner_mutant(35)
 def test_owner_gen4(self):self.owner_mutant(0)
 def owner_mutant(self,bit):
  r=self.new();self.assertFalse(r.ack(r.owner^(1<<bit),17,17));self.assertTrue(r.fault);self.assertTrue(r.pending)
 def test_slot9(self):
  r=self.new();self.assertFalse(r.ack(r.owner,18,17));self.assertTrue(r.fault)
 def test_checked_does_not_authorize_changed_current_tuple(self):
  r=self.new();r.ack(r.owner,17,17);self.assertFalse(r.ack(r.owner^1,17,17));self.assertTrue(r.pending)
 def test_provider_fault_current_correct_tuple(self):
  r=self.new();self.assertFalse(r.ack(r.owner,17,17,True));self.assertTrue(r.fault)
 def test_duplicate_after_consume(self):
  r=self.new();r.ack(r.owner,17,17);r.ack(r.owner,17,17)
  self.assertFalse(r.ack(r.owner,17,17));self.assertTrue(r.fault)
 def test_reset_preserves_pending_debt(self):
  r=self.new();r.reset();self.assertTrue(r.pending);self.assertTrue(r.fault)
  with self.assertRaises(ValueError):r.accept_root(0)
 def test_second_write_exclusion(self):
  r=self.new()
  with self.assertRaises(ValueError):r.write(18)
 def test_unowned_ack_refuses(self):
  r=M.ACKReference();self.assertFalse(r.ack(1,17,17));self.assertTrue(r.fault)
 def test_positive_composition(self):
  m=M.compose();self.assertEqual(m['calendar']['cycles_conditional'],127)
  self.assertAlmostEqual(m['calendar']['ns_conditional'],127/1.2)
  self.assertGreater(M.compose(2,2)['calendar']['cycles_conditional'],127)
 def test_no_free_match_or_provider_edge(self):
  with self.assertRaises(ValueError):M.compose(0,1)
  with self.assertRaises(ValueError):M.compose(1,0)
 def test_existing_protected_padding_once(self):
  m=M.compose();r=m['retained_control'];self.assertEqual(r['reused_padding_bits'],11);self.assertEqual(r['new_physical_FFs'],0)
  self.assertEqual(m['W6_receiver_join']['protected_bits'],144);self.assertEqual(m['W6_receiver_join']['new_coded_words'],0)
 def test_actual_provider_storage_cost(self):
  c=M.compose()['costs'];self.assertEqual(c['provider_total_new_FFs'],128)
  self.assertEqual(c['provider_raw_accepted_tuple_bits'],55);self.assertEqual(c['provider_protected_ACK_bits'],72)
  self.assertGreater(c['cell_um2_ASSUMED'],0);self.assertGreater(c['async_reset_buffer_cell_area_um2_ASSUMED'],0)
 def test_commonclock_CDC_is_selected_not_unknown_zero(self):
  a=M.compose()['adapter_selection'];self.assertEqual(a['CDC_seats'],0);self.assertIn('same literal clock',a['CDC_zero_proof'])
 def test_physical_and_fullprogram_remain_open(self):
  m=M.compose();self.assertFalse(m['scope']['physical_build']);self.assertIsNone(m['physical']['slot_fit']);self.assertIsNone(m['calendar']['whole_token_ns'])
 def test_goodall_owner_protocol_pinned(self):
  r=json.loads(M.inputs()['Goodall_owner55_contract.json']);self.assertEqual(r['mapping']['host_ACK55'],'{W4.ack_owner, W4.ack_slot}')
 def test_actual_source_API(self):
  s=(ROOT/'rtl/experimental/hbm_c0_connected_20261003/r3/ot_gpu_c0_connected_bridge_r3.sv').read_text()
  self.assertIn('next_raw[204:196]=local_wr_addr',s)
  self.assertIn('.host_ack_identity({local_ack_owner,local_ack_slot})',s)
  self.assertIn('tuple_match && ACK_checked',s)
  self.assertNotIn('.host_ack_identity(identity)',s)
if __name__=='__main__':unittest.main()
