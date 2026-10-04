"""Actual source install and finite-hook tests; no HDL execution or inference."""
import json,tempfile,threading,unittest
from pathlib import Path
from tools.gpu_sys import canonical_qwen_matrix_tc_install as I
from tools.gpu_sys import canonical_qwen_matrix_tc_factory as F
from tools.gpu_sys import canonical_qwen_matrix_tc_pins as T
from tools.gpu_sys import canonical_qwen_matrix_services as S
R=Path(__file__).resolve().parents[2]
B=R/'results/uarch/qwen_matrix_tc_install_20261003/base_9d06'
O=R/I.DEFAULT_OUT
class Root:
 def __init__(self):
  self.book=json.loads((O/'ports.json').read_text());self.v={};self.writes=[];self.edges=0;self.evals=0
  self.lock=threading.RLock();self.hooks=[]
 def get(self,n):return self.v.get(n,0)
 def set(self,n,v):self.writes.append((n,v));self.v[n]=v
 def component(self,b,i,aliases=None):return Pins(self,b,i,aliases)
 def tick(self):self.edges+=1
 def settle(self):self.evals+=1
class Pins:
 def __init__(self,r,b,i,a):self.root=r;self.block=b;self.index=i;self.aliases=a or {}
 def parameter(self,n):return {'ENABLE_CLIENT':1,'INDEX':self.index}[n]
class Provider:
 pass
for n in S.MatrixPhysicalServices.REQUIRED:setattr(Provider,n,lambda self,*a:None)
class Tests(unittest.TestCase):
 def test_actual64_TC_source_and_consumption(self):
  s=(O/(json.loads((O/'ports.json').read_text())['top']+'.sv')).read_text()
  self.assertIn('for(genvar i=0;i<64;i=i+1)begin:g_actual_tc',s)
  self.assertIn('ot_gpu_sm_q #(.SUB(4),.LS(32),.NC(16)',s)
  self.assertIn('.clk(stream_clk)',s);self.assertIn('.rst_n(sm_rst_n[i])',s)
  self.assertIn('assign tc_consume_valid[i]=u_sm.w_valid && u_sm.w_ready;',s)
  self.assertIn('parameter bit ENABLE_TC=0',s)
  self.assertNotIn('assign tc_rdata[i*512 +: 512]=expected',s)
 def test_existing_mux_and_owner_wiring_unchanged(self):
  book=json.loads((B/'ports.json').read_text());s=(B/(book['top']+'.sv')).read_text()
  out=(O/(book['top']+'.sv')).read_text()
  for block in ['g_scratch_client','g_source_owner']:
   original=s[s.index('begin:'+block):s.index('end\n',s.index('begin:'+block))+4]
   self.assertIn(original,out)
  for n,p in book['pins'].items():self.assertEqual(p,json.loads((O/'ports.json').read_text())['pins'][n])
 def test_driver_only_actual_TC_inputs(self):
  d=(O/'pin_driver.cpp').read_text().split('else if(op=="SET")')[1]
  for n,(direction,w) in T.FIELDS.items():
   self.assertEqual('name=="tc_'+n+'"' in d,direction=='input')
 def test_source_dependencies_no_duplicate_differing_definitions(self):
  book=json.loads((O/'ports.json').read_text());paths=(O/'sources.f').read_text().splitlines()
  self.assertEqual(len(paths),len(set(paths)))
  for path in paths:self.assertEqual(I.sha(R/path),book['source_sha256'][path])
  self.assertIn(T.SOURCE,paths)
 def test_cold_generation_byte_equal(self):
  # Exact repository-relative paths are part of the pinbook/source list.
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);book=json.loads((O/'ports.json').read_text())
   paths=set(book['source_sha256'])|{*I.ENGINE_DEPENDENCIES,T.SOURCE,
    'results/uarch/qwen_matrix_scratch_adapter_20261003/tc_model_ready.json'}
   paths.discard(str((O/(book['top']+'.sv')).relative_to(R)))
   for path in paths:
    p=root/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((R/path).read_bytes())
   base=root/B.relative_to(R);base.mkdir(parents=True,exist_ok=True)
   for n in ['ports.json','sources.f','pin_driver.cpp',book['top']+'.sv']:(base/n).write_bytes((B/n).read_bytes())
   out=I.generate(root,base,I.DEFAULT_OUT)
   for n in ['ports.json','sources.f','pin_driver.cpp',book['top']+'.sv']:
    self.assertEqual((out/n).read_bytes(),(O/n).read_bytes())
 def test_enabled_actual_TC_constructor_has_no_edges(self):
  r=Root();r.v['tc_enabled']=1;f=F.MatrixFactory(r,{(1,24):Provider()},None,enabled=True)
  self.assertEqual(f.bindings[(1,24)][0].index,56);self.assertEqual(r.edges,0)
  self.assertEqual(r.evals,0);self.assertEqual(r.hooks,[])
  self.assertIsInstance(f.bindings[(1,24)][1],F.SharedConsumption)
 def test_missing_TC_enabled_provider_and_source_manifest_refusals(self):
  r=Root()
  with self.assertRaises(ValueError):F.MatrixFactory(r,{(0,0):Provider()},None,enabled=True)
  r.v['tc_enabled']=1
  with self.assertRaises(ValueError):F.MatrixFactory(r,{(0,0):object()},None,enabled=True)
  with self.assertRaises(ValueError):F.MatrixFactory(r,{},None,enabled=True)
  r.book['inventory']['source_owner_count']=0
  with self.assertRaises(ValueError):F.MatrixFactory(r,{(0,0):Provider()},None,enabled=True)
 def test_shared_consumption_settles_without_extra_edge(self):
  r=Root();r.v['tc_enabled']=1;f=F.MatrixFactory(r,{(0,0):Provider()},None,enabled=True)
  p,a,s=f.bindings[(0,0)];a.before_edge();a.after_edge()
  self.assertEqual(r.evals,1);self.assertEqual(r.edges,0)
 def test_factory_enrollment_reuses_ONE_builder_hook(self):
  r=Root();r.v['tc_enabled']=1;f=F.MatrixFactory(r,{(0,0):Provider()},None,enabled=True)
  def builder(root,authority,handlers,w2,*,matrix_services,enabled):
   self.assertIs(root,r);self.assertTrue(enabled)
   root.hooks.append(object())
   for s in matrix_services:s.installed=True
   return {'matrix_services':matrix_services}
  result=f.enroll(builder,object(),{},[],enabled=True)
  self.assertIs(result['matrix_factory'],f);self.assertEqual(len(r.hooks),1);self.assertEqual(r.edges,0)
  with self.assertRaises(ValueError):f.enroll(builder,object(),{},[],enabled=True)
 def test_controller_refuses_without_real_hook(self):
  r=Root();r.v['tc_enabled']=1;f=F.MatrixFactory(r,{(0,0):Provider()},None,enabled=True)
  with self.assertRaises(ValueError):f.controller(2,0,0)
  with self.assertRaises(ValueError):f.controller(2,0,1)
if __name__=='__main__':unittest.main()
