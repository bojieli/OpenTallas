import hashlib, importlib.util, io, json, unittest
from pathlib import Path
from tools.gpu_sys.canonical_qwen_ranked_simulator import RankedEnclosingPins,RankedPhysicalSectorAuthority
from tools.gpu_sys.canonical_qwen_transport import TransportError
ROOT=Path(__file__).resolve().parents[4];D=Path(__file__).resolve().parent

class RankedSourceTests(unittest.TestCase):
 def test_source_qualified_counts_and_inner_PC(self):
  b=json.loads((D/'ports.json').read_text());s=(D/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
  self.assertEqual(b['inventory']['W2_total'],256);self.assertEqual(b['inventory']['W2_PC_per_rank'],128)
  self.assertIn('rank<2',s);self.assertIn('i<128',s);self.assertIn(".PC_ID(7'(i))",s)
  self.assertNotIn("PC_ID(8'",s);self.assertIn('rank*128+i',s)
  self.assertEqual(b['pins']['w2_c_req_v']['bits'],1536)
  self.assertEqual(b['pins']['w2_p_req_v']['count'],256)
  self.assertEqual(s.count('ot_gpu_qwen_joined_kv #'),1)
 def test_all_actual_source_pins_and_no_stub(self):
  b=json.loads((D/'ports.json').read_text())
  for p,h in b['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
  self.assertEqual(hashlib.sha256((D/'model.json').read_bytes()).hexdigest(),b['rank_model_sha256'])
  guard=(D/'ot_gpu_qwen_rank_boundary.sv').read_text()
  self.assertIn('reverse_rank==grant_identity[136]',guard)
  self.assertIn('map_rank==alloc_source[56]',guard)
  self.assertIn('ENABLE=0',guard);self.assertNotIn('always',guard)
 def test_rank_port_bounds_and_inner_identity(self):
  p=RankedEnclosingPins(io.StringIO('ot_gpu_qwen_hbm_integrated_ranked ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128\n'),io.StringIO())
  for r in (0,1):
   for pc in range(128):
    leaf=p.component('w2',pc,rank=r)
    self.assertEqual(leaf.index,r*128+pc);self.assertEqual(leaf.parameter('PC_ID'),pc);self.assertEqual(leaf.parameter('RANK_ID'),r)
  for pc,r in ((128,0),(0,2),(0,None),(-1,0)):
   with self.assertRaises(TransportError):p.component('w2',pc,rank=r)
 def test_old_or_disabled_actual_driver_refused(self):
  for hello in ('ot_gpu_qwen_hbm_integrated ENABLE=1 SM=64 W2=128','ot_gpu_qwen_hbm_integrated_ranked ENABLE=0 SM=64 W2=256 RANKS=2 PC_PER_RANK=128'):
   with self.assertRaises(TransportError):RankedEnclosingPins(io.StringIO(hello+'\n'),io.StringIO())
 def test_key_rank_not_client_tag_truncation(self):
  self.assertEqual(RankedPhysicalSectorAuthority.bank({'key':0,'PC':127}),(0,127))
  self.assertEqual(RankedPhysicalSectorAuthority.bank({'key':1<<13,'PC':127}),(1,127))
 def test_generator_byte_reproduction(self):
  paths=['ports.json','sources.f','pin_driver.cpp','ot_gpu_qwen_hbm_integrated_ranked.sv']
  before={p:(D/p).read_bytes() for p in paths}
  spec=importlib.util.spec_from_file_location('ranked_generate',D/'generate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.main()
  for p in paths:self.assertEqual(before[p],(D/p).read_bytes(),p)

if __name__=='__main__':unittest.main()
