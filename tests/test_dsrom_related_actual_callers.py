import hashlib,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/dsrom_seven_class_swap_20261003'
RTL=ROOT/'rtl/model_ready_ds_seven_class_20261003'
class ActualCallers(unittest.TestCase):
 def test_index_arithmetic_retained(self):
  old=(D/'inputs/idx_pool_adapt.sv').read_text();new=(RTL/'ot_hdc_v41x_idx_pool_adapt_related_vm.sv').read_text()
  mark='    // Convert each QDQ4 block'
  self.assertEqual(old[old.index(mark):],new[new.index(mark):])
  self.assertIn('if(!VM_RESPONSE_WAIT)begin q1_e<=qe;q2_e<=q1_e;end',new)
  self.assertIn('x_reply_cookie!=q1_e',new)
  self.assertIn('!read_pending && !(|x_re) && !q2_v && !identity_fault',new)
 def test_vec_arithmetic_retained(self):
  old=(D/'inputs/vec.sv').read_text();new=(RTL/'ot_hdc_v41x_vec_related_kv.sv').read_text()
  mark='    assign side_v ='
  self.assertEqual(old[old.index(mark):],new[new.index(mark):])
  self.assertIn('!KV_BACKPRESSURE || !kv_destination || kv_launch_credit',new)
 def test_no_free_four_transaction_credits(self):
  m=json.loads((D/'model.json').read_text())
  for plane in m['planes']:self.assertEqual(plane['transaction_credit_seats'],1)
  s=m['actual_implementation_work']['SU_launch_credit']
  self.assertEqual(s['serializer_state_bits'],16420+16369)
  self.assertEqual(s['named_state']['FIFO_bits_charged_in_existing_class0_plane'],s['forward_related_state_bits'])
 def test_grant_cannot_retire_KV(self):
  s=(RTL/'ot_chip_v41x_kv_prefetch_visible.sv').read_text()
  for i in range(4):self.assertIn(f'(wr_live[{i}] && m_wr_done[{i}])',s)
  self.assertIn('!wr_live[ms] && !wq_oor_s[ms] && !fault',s)
  bridge=(RTL/'ot_ds_su_kv_related_visible.sv').read_text()
  self.assertIn('sink_visible&&retired_ready&&!kv_fault',bridge)
  self.assertIn('(abort_slow||!slow_rst_n)&&reserved',bridge)
 def test_actual_native_geometry_and_clocks(self):
  m=json.loads((D/'model.json').read_text())
  self.assertEqual(m['actual_field_x_bridge']['native_macros'],256)
  self.assertEqual(m['actual_field_x_bridge']['mutable_bits'],2*1024*1024*8)
  self.assertFalse(m['admission']['physical_build'])
  self.assertFalse(m['admission']['protected_parent_integration'])
 def test_full_KV_queue_regression_present(self):
  s=(ROOT/'tests/rtl/dsrom_su_kv_visible/tb.sv').read_text()
  self.assertIn('wait(dut.native_KV.wq_n[0]==128)',s)
  self.assertIn('wait(completes==260)',s)
  self.assertIn('if(!debt||!quarantine||credit)',s)
 def test_archived_terminal_and_sources(self):
  d=D/'actual_callers';m=json.loads((d/'implementation.json').read_text())
  for name,digest in m['artifact_sha256'].items():self.assertEqual(hashlib.sha256((d/name).read_bytes()).hexdigest(),digest,name)
  for entry in m['implemented_callers'].values():
   record=json.loads((d/entry['record']).read_text())
   self.assertEqual(record['compile']['exit_code'],0);self.assertEqual(record['simulation']['exit_code'],0)
   self.assertIn(entry['terminal'],record['terminal'])
  self.assertFalse(m['full_seven_class_parent_integrated'])
if __name__=='__main__':unittest.main()
