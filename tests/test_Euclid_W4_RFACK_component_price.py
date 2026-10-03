import sys,pathlib,tempfile,unittest,json
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'tools'))
import Euclid_W4_RFACK_component_price as m
class Price(unittest.TestCase):
 def test_canonical_fields(self):
  x=m.price();self.assertEqual(x['canonical_owner']['bits'],46);self.assertEqual(x['selected_inventory']['raw_identity_payload_bits_per_SM'],55);self.assertEqual(x['owner_generation_separate_FFs'],0);self.assertEqual(x['selected_inventory']['leaf_raw_capture_FFs'],1760)
 def test_full_retention_and_ports_priced(self):
  i=m.price()['selected_inventory'];self.assertEqual(i['total_added_FFs'],6368);self.assertEqual(i['common_ACKs_per_write'],1);self.assertEqual(i['internal_SIMD_protected_retention_FFs'],2304);self.assertEqual(i['SRAM_added_ports'],0);self.assertGreater(i['host_internal_mux_bit_equivalents'],0)
 def test_prospective_not_measured(self):
  x=m.price();self.assertGreater(x['latency']['added_local_RF_edges_vs_existing_ACK'],0);self.assertIsNone(x['latency']['actual_clock']);self.assertIsNone(x['latency']['finite_wait_upper']);self.assertFalse(x['admission']['hardware_build']);self.assertFalse(x['admission']['headline']);self.assertIsNone(x['area']['full_component_area_um2']);self.assertGreater(x['area']['subtotal_footprint_um2_ASSUMED'],0)
 def test_no_directory_or_generation_cap(self):
  x=m.price();self.assertEqual(x['source_context']['NC_full_wrapper'],6);self.assertEqual(x['source_context']['new_directory_client'],0);self.assertFalse(x['quiescence']['generation_run_cap']);self.assertIsNone(x['source_context']['accepted_C0_KV_caller_map']);self.assertTrue(x['quiescence']['matched_reverse_CDC_before_reuse'])
 def test_reject_owner_slice_mutant(self):
  old=m.R
  with tempfile.TemporaryDirectory() as t:
   m.R=pathlib.Path(t)
   for p in old.iterdir():
    if p.is_file():(m.R/p.name).write_bytes(p.read_bytes())
   p=m.R/'canonical-fullwidth-C0-KV-read-r1.json';x=json.loads(p.read_text());x['canonical_owner']['bits']=42;p.write_text(json.dumps(x))
   try:
    with self.assertRaises(ValueError):m.price()
   finally:m.R=old
if __name__=='__main__':unittest.main()
