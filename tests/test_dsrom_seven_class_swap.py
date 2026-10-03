import hashlib,json,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/dsrom_seven_class_swap_20261003'
class Join(unittest.TestCase):
 def setUp(self):self.m=json.loads((D/'model.json').read_text())
 def test_inputs(self):
  for n,p in self.m['source_pins'].items():self.assertEqual(hashlib.sha256((D/'inputs'/n).read_bytes()).hexdigest(),p['sha256'])
 def test_all_classes(self):self.assertEqual(set(p['class_id'] for p in self.m['planes']),set(range(7)));self.assertEqual(len(self.m['planes']),14)
 def test_actual_widths(self):
  p={p['name']:p['payload_bits'] for p in self.m['planes']}
  self.assertEqual(p['su_kv_staging'],256*(1+30+32));self.assertEqual(p['me_result_write'],4*(1+30+16+16*32));self.assertEqual(p['field_row_write'],128*(1+30+32));self.assertEqual(p['selector_read_reply'],4*16*32)
 def test_state(self):self.assertEqual(self.m['state_total_bits'],sum(8*(p['payload_bits']+456)+52+230 for p in self.m['planes']))
 def test_no_transfer(self):self.assertFalse(self.m['admission']['physical_build']);self.assertFalse(self.m['admission']['protected_parent_integration']);self.assertFalse(self.m['reset']['empty_is_retirement'])
 def test_charge(self):
  for p in self.m['planes']:self.assertEqual(p['no_stall_crossing_cycles'],2)
 def test_credit_II(self):
  for p in self.m['planes']:
   self.assertEqual(p['transaction_credit_seats'],1)
   self.assertEqual(p['FIFO_storage_depth'],4)
   self.assertFalse(p['initiation_interval']['finite_upper_bound'])
   self.assertGreater(p['initiation_interval']['no_stall_zero_caller_service_bound_ps'],4000)
 def test_real_caller_not_promoted(self):
  self.assertFalse(self.m['issuer_binding']['actual_enrollment'])
  self.assertFalse(self.m['issuer_binding']['admission'])
 def test_retained_arithmetic_source(self):
  old=(D/'inputs/spine.sv').read_text()
  new=(ROOT/'rtl/model_ready_ds_seven_class_20261003/ot_v41_spine_related_vm.sv').read_text()
  # Capture mux may change the input binding; arithmetic itself must be literal retained source.
  self.assertEqual(old[old.index('    // buffers'):],new[new.index('    // buffers'):].replace('checked_x_q','x_q'))
  a="            x_re <= 1'b0; rq_v <= x_re;"
  b='            // loaded counts:'
  retained=old[old.index(a):old.index(b)]
  self.assertIn(retained,new)
if __name__=='__main__':unittest.main()
