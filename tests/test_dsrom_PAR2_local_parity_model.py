import ast,gzip,importlib.util,json,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('parity',ROOT/'tools/dsrom_PAR2_local_parity_model.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ParityService(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.result,cls.placed,cls.obs=m.build();cls.provider=json.loads(gzip.decompress((m.BASE/'inputs/ECC_directory.jsonl.gz').read_bytes()).splitlines()[0])
 def test_source_API_address_boundaries(self):
  tree=ast.parse((m.BASE/'inputs/sidecar_address_source.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sidecar_address');ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'pinned_source','exec'),ns)
  for bit in [0,15,255,256,8192*256-1,8192*256,16384*256,self.provider['bits']-1]:
   src=ns['sidecar_address'](self.provider,bit)
   self.assertEqual(m.address(self.provider,bit),(src['pair'],src['mb'],src['parity'],src['physical_row'],src['data_bit']))
  with self.assertRaises(ValueError):m.address(self.provider,self.provider['bits'])
 def test_real_storage_only_and_no_source_deletion(self):
  c=self.result['conservation'];self.assertEqual(c['leaves'],412);self.assertEqual(c['replica_useful_capacity_bits'],432013312);self.assertTrue(c['original_shard0_storage_retained']);self.assertTrue(c['no_adjacent_q_BF_compute_added']);self.assertEqual(len(self.placed),412)
 def test_64_conflicting_rows_take64_service_rounds(self):
  w=self.result['finite_service']['first_address_batch_witness'];rounds,words=m.service_batch(self.provider,w['requests_pair_linearbit']);self.assertEqual((rounds,words),(64,64));self.assertFalse(self.result['finite_service']['actual_simultaneous_engine_issue_proven'])
 def test_coalescing_requires_same_row(self):
  self.assertEqual(m.service_batch(self.provider,[(2048,0),(2049,16)]),(1,1))
  self.assertEqual(m.service_batch(self.provider,[(2048,0),(2049,512)]),(2,2))
  with self.assertRaises(ValueError):m.service_batch(self.provider,[(2048,1)])
 def test_finite_seats_fail_closed(self):
  with self.assertRaises(ValueError):m.service_batch(self.provider,[(2048,0),(2048,16)])
  with self.assertRaises(ValueError):m.service_batch(self.provider,[(2048+i,i*16) for i in range(129)])
 def test_no_free_throughput_or_latency(self):
  f=self.result['finite_service'];self.assertEqual(f['per_batch_read_round_upper'],128);self.assertFalse(f['conflict_free_one_cycle_service']);self.assertTrue(f['source_unbackpressured_engine_cannot_use_this_contract_without_owned_accept_ready_adapter']);self.assertFalse(self.result['physical_GO'])
 def test_all_source_phases_and_price_retained(self):
  self.assertEqual(self.result['finite_service']['source_FP4_matrices'],46080);a=self.result['area'];self.assertGreater(a['full_added_debit_mm2'],9);self.assertGreater(a['against_clearance_priced_screen_remaining_mm2'],120);self.assertFalse(a['fit_certified']);self.assertTrue(a['no_residual418_or47_credit'])
 def test_real_OBS_and_disjoint_geometry(self):
  self.assertTrue(self.result['geometry']['raw_bodies_halos_logic_disjoint_from_parent_macros']);self.assertGreater(len(self.obs),1000);self.assertLess(self.result['geometry']['last_y_DBU'],16000000)
if __name__=='__main__':unittest.main()
