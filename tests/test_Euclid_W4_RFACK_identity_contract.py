import importlib.util,pathlib,tempfile,unittest,json
P=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('w4',P/'tools/Euclid_W4_RFACK_identity_contract.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class W4(unittest.TestCase):
 def test_source_contract(self):
  x=m.model();self.assertFalse(x['hardware_admitted']);self.assertIsNone(x['ports']['write_generation_bits']);self.assertEqual(x['source_inventory']['common_ACK_per_write'],1)
  self.assertTrue(all(v is None for v in x['unknown'].values()))
 def test_sizing_not_admission(self):
  x=m.model(16,2);self.assertEqual(x['candidate_inventory']['identity_bits_per_die'],864);self.assertFalse(x['hardware_admitted']);self.assertIsNone(x['unknown']['composed_incremental_cycles'])
 def test_embedded_generation_not_doublecharged(self):
  x=m.model(16,4,generation_in_tag=True);self.assertEqual(x["candidate_inventory"]["identity_bits_per_SM"],25);self.assertEqual(x["candidate_inventory"]["identity_bits_per_die"],800);self.assertFalse(x["hardware_admitted"])
 def test_invalid_width_or_replica(self):
  for a in [(0,1,32),(16,0,32),(16,True,32),(16,1,1)]:
   with self.assertRaises(ValueError):m.model(*a)
 def test_acceptance_pin_mutant(self):
  old=m.RECORD
  with tempfile.TemporaryDirectory() as t:
   m.RECORD=pathlib.Path(t); pins=json.loads((old/'source-pins-r1.json').read_text());(m.RECORD/'source-pins-r1.json').write_text(json.dumps(pins))
   p='rtl/gpu/ot_gpu_rf_service.sv';dst=m.RECORD/'inputs'/p;dst.parent.mkdir(parents=True);dst.write_bytes((old/'inputs'/p).read_bytes().replace(b'wr_valid && wr_ready',b'wr_valid'))
   try:
    with self.assertRaises(ValueError):m.model()
   finally:m.RECORD=old
if __name__=='__main__':unittest.main()
