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
if __name__=='__main__':unittest.main()
