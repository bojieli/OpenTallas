import unittest,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];D=ROOT/'rtl/model/qwen_hbm_integrated_20261003/scratch'
class InstalledScratch(unittest.TestCase):
 def test_actual_service_sources_and_direction(self):
  b=json.loads((D/'ports.json').read_text());s=(D/(b['top']+'.sv')).read_text()
  for n in ('valid','write','addr','wdata','done_ready'):
   self.assertEqual(b['pins']['scratch_client_'+n]['direction'],'input')
   self.assertEqual(b['pins']['sm_scratch_'+n]['direction'],'output')
   self.assertEqual(b['pins']['scratch_service_'+n]['direction'],'output')
   self.assertIn('.scratch_'+n+'(scratch_service_'+n,s)
  for n in ('ready','done','rdata'):
   self.assertEqual(b['pins']['scratch_client_'+n]['direction'],'output')
   self.assertEqual(b['pins']['scratch_service_'+n]['direction'],'output')
  self.assertIn('.shared_router_drained(kv_shared_drained && (&scratch_drained))',s)
  self.assertIn('.por_n(sm_rst_n[i])',s)
  self.assertIn('.ENABLE_CLIENT(ENABLE && ENABLE_SCRATCH_CLIENT)',s)
  self.assertEqual(b['inventory']['new_SRAM_macros'],0)
 def test_source_book_exact(self):
  b=json.loads((D/'ports.json').read_text())
  for p,h in b['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
  driver=(D/'pin_driver.cpp').read_text();a=driver.index('else if(op=="SET")');writes=driver[a:]
  self.assertNotIn('name=="sm_scratch_valid"',writes)
  self.assertNotIn('name=="scratch_service_ready"',writes)
  self.assertIn('name=="scratch_client_valid"',writes)
 def test_originals_unchanged_against_pricing(self):
  m=json.loads((ROOT/'rtl/model/qwen_scratch_client_mux_20261003/model.json').read_text())
  for p,h in m['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/p).read_bytes()).hexdigest(),h,p)
if __name__=='__main__':unittest.main()
