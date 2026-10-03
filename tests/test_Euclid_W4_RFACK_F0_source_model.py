import pathlib,sys,unittest,tempfile,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import Euclid_W4_RFACK_F0_source_model as m
class W4F0(unittest.TestCase):
 def test_width_and_cost_inventory(self):
  x=m.contract();i=x['leaf_incremental_inventory'];self.assertEqual(i['captured_identity_bits_per_SM'],55);self.assertEqual(i['captured_identity_bits_per_die'],1760);self.assertEqual(i['independent_mirror_ACK_channels'],0)
 def test_original_identity_and_namespace(self):
  x=m.contract();i=x['source_identity'];self.assertEqual(i['PTAGW'],35);self.assertEqual(i['CTAGW'],32);self.assertFalse(i['original_tag_overwritten']);self.assertTrue(i['generation_is_explicit']);self.assertIsNone(x['W2_boundary']['production_C0_KV_caller_map'])
 def test_continuous_unknowns(self):
  x=m.contract();self.assertFalse(x['hardware_admitted']);self.assertIsNone(x['allcopy_reuse']['actual_quiescence_wait_cycles']);self.assertTrue(x['allcopy_reuse']['no_arbitrary_token_or_generation_cap']);self.assertEqual(x['wholeprogram']['DS_PC_count'],2213);self.assertEqual(x['wholeprogram']['Qwen_PC_count'],1737);self.assertIsNone(x['model_admission']['composed_cycles'])
 def test_reject_frozen_contract_mutant(self):
  old=m.F0
  with tempfile.TemporaryDirectory() as t:
   m.F0=pathlib.Path(t)
   for p in old.iterdir():
    if p.is_file():(m.F0/p.name).write_bytes(p.read_bytes())
   p=m.F0/'W2-interface-contract-r1.json';x=json.loads(p.read_text());x['W2_model_extension']['original_client_tag_bits']=16;p.write_text(json.dumps(x))
   try:
    with self.assertRaises(ValueError):m.contract()
   finally:m.F0=old
if __name__=='__main__':unittest.main()
