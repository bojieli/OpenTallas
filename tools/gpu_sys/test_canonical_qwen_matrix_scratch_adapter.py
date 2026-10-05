import copy,json,threading,unittest
from pathlib import Path
from tools.gpu_sys import canonical_qwen_matrix_scratch_adapter as A
from tools.gpu_sys import canonical_qwen_matrix_tc_pins as T
from tools.gpu_sys import canonical_qwen_matrix_services as S
ROOT=Path(__file__).resolve().parents[2]
class Root:
 def __init__(self):
  self.book=json.loads((ROOT/'results/uarch/qwen_matrix_scratch_adapter_20261003/inputs/euclid_ports.json').read_text())
  self.v={};self.writes=[];self.edges=0;self.lock=threading.RLock()
 def component(self,b,i,aliases=None):return Pins(self,b,i,aliases)
 def get(self,n):return self.v.get(n,0)
 def set(self,n,v):self.v[n]=v;self.writes.append((n,v))
 def tick(self):self.edges+=1
class Pins:
 def __init__(self,r,b,i,a=None):self.root=r;self.block=b;self.index=i;self.aliases=a or {}
 def parameter(self,n):return {'ENABLE_CLIENT':1,'INDEX':self.index}[n]
 def get(self,n):return self.root.get(self.block+'_'+self.aliases.get(n,n))
 def set(self,n,v):self.root.set(self.block+'_'+self.aliases.get(n,n),v)
 def settle(self):pass
class Tests(unittest.TestCase):
 def binding(self):
  r=Root();p=A.ScratchPump(r.component('scratch',24,aliases=A.ALIASES))
  identity=dict(session=1,source_PC=2,native_tag=3,native_generation=4,rank=0,SM=24,
                output_version_id=5,range_begin=0,range_end=2,owner55=197)
  origin=dict(identity=identity,GO_tuple239=S.pack_GO(identity))
  reservation=dict(identity=identity,scratch_base=80,rows=128)
  r.v.update(scratch_workspace_valid=1,scratch_workspace_exclusive=1,
   scratch_workspace_owner=197,scratch_workspace_tuple=origin['GO_tuple239'],
   scratch_workspace_base=80,scratch_workspace_length=128,scratch_drained=1)
  p.bind(reservation,origin);return r,p,origin
 def test_command_drives_actual_input_offer_identity(self):
  r,p,o=self.binding();p.start(80,bytes(64));p.before_edge()
  self.assertIn(('scratch_client_tuple',o['GO_tuple239']),r.writes)
  self.assertIn(('scratch_client_owner',197),r.writes)
  self.assertTrue(all(n.startswith('scratch_client_') for n,v in r.writes))
  self.assertEqual(r.edges,0)
 def test_no_SM_outputs_or_width_mismatch(self):
  r=Root()
  with self.assertRaises(ValueError):A.ScratchPump(r.component('sm',0,aliases=S.SCRATCH_ALIASES))
  for field,mut in [('client_valid',{'direction':'output'}),('client_tuple',{'leaf_bits':238})]:
   r=Root();r.book['pins']['scratch_'+field].update(mut)
   with self.assertRaises(ValueError):A.ScratchPump(r.component('scratch',0,aliases=A.ALIASES))
 def test_source_GO_and_home_mismatch(self):
  r,p,o=self.binding();p.binding=None
  for mut in [{'scratch_base':80,'rows':128,'identity':dict(o['identity'],native_tag=5)},
              {'scratch_base':80,'rows':128,'identity':dict(o['identity'],SM=25)}]:
   with self.assertRaises(ValueError):p.bind(mut,o)
 def test_address_no_shape_guess(self):
  r,p,o=self.binding()
  for addr in (79,208):
   with self.assertRaises(ValueError):p.start(addr)
 def test_return_identity_change_fault_retains(self):
  r,p,o=self.binding();p.start(80);r.v['scratch_client_ready']=1;p.before_edge();p.after_edge()
  self.assertEqual(p.phase,'done');r.v['scratch_workspace_tuple']^=1
  with self.assertRaises(ValueError):p.before_edge()
  self.assertTrue(p.faulted);self.assertIsNotNone(p.binding);self.assertEqual(p.phase,'done')
 def test_actual_done_and_drained_only(self):
  r,p,o=self.binding();p.start(80);r.v['scratch_client_ready']=1;p.before_edge();p.after_edge()
  self.assertIsNone(p.take());r.v.update(scratch_client_done=1,scratch_client_rdata=41)
  p.before_edge();p.after_edge();self.assertEqual(p.take(),(41).to_bytes(64,'little'))
  r.v['scratch_busy']=1
  with self.assertRaises(ValueError):p.unbind()
  self.assertIsNotNone(p.binding);r.v['scratch_busy']=0;p.unbind();self.assertIsNone(p.binding)
 def tc(self):
  r=Root();r.book['matrix_TC_contract']=dict(module='ot_gpu_sm_q',parameters=T.PARAMS,
   source_sha256='a'*64,consume_tap='u_sm.w_valid && u_sm.w_ready')
  r.book['source_sha256'][T.SOURCE]='a'*64
  for n,(d,w) in T.FIELDS.items():r.book['pins']['tc_'+n]=dict(direction=d,leaf_bits=w,count=64,bits=w*64)
  return r
 def test_genuine_TC_defaultoff_and_no_SIMD_substitution(self):
  r=self.tc()
  with self.assertRaises(ValueError):T.TCPins(r,0,0)
  r.book['matrix_TC_contract']['module']='ot_gpu_full_sm_service_guarded'
  with self.assertRaises(ValueError):T.TCPins(r,0,0,enabled=True)
 def test_TC_actual_boundary_width_and_source_identity(self):
  for k,v in [('rsp_data',{'leaf_bits':512}),('start',{'direction':'output'})]:
   r=self.tc();r.book['pins']['tc_'+k].update(v)
   with self.assertRaises(ValueError):T.TCPins(r,0,0,enabled=True)
  r=self.tc();r.book['source_sha256'][T.SOURCE]='b'*64
  with self.assertRaises(ValueError):T.TCPins(r,0,0,enabled=True)
 def test_TC_exact_operand_bytes_and_same_edge(self):
  r=self.tc();p=T.TCPins(r,1,24,enabled=True)
  p.set('rsp_data',17);self.assertEqual(r.get('tc_rsp_data'),17<<(56*1024))
  r.v['tc_rdata']=29<<(56*512);self.assertEqual(p.get('rdata'),29)
  self.assertEqual(r.edges,0);p.tick();self.assertEqual(r.edges,1)
  for name,value in [('rdata',0),('rsp_data',1<<1024),('rsp_tag',1024)]:
   with self.assertRaises(ValueError):p.set(name,value)
 def test_consumption_requires_actual_shared_edge_and_saved_fullGO(self):
  r=self.tc();p=T.TCPins(r,0,0,enabled=True);a=T.ConsumptionAuthority(object(),p)
  class Service:pass
  service=Service();service.a=a;service.origin={'GO_tuple239':81}
  service.line={'tag':7,'plan':{'line_address':3},'phase':'consume','reservation':{'identity':8}}
  a.attach(service);a.before_edge();a.after_edge()
  self.assertFalse(a.matrix_weight_consumed(7,3,{'identity':8}))
  r.v['tc_consume_valid']=1;a.before_edge()
  self.assertFalse(a.matrix_weight_consumed(7,3,{'identity':8}))
  a.after_edge()
  with self.assertRaises(ValueError):a.matrix_weight_consumed(8,3,{'identity':8})
  self.assertIsNotNone(a.accepted)
  self.assertTrue(a.matrix_weight_consumed(7,3,{'identity':8}))
  self.assertFalse(a.matrix_weight_consumed(7,3,{'identity':8}))
 def test_TC_preserves_source_all290_full_loop_latency(self):
  m=T.compose(ROOT);self.assertEqual(len(m['operation_floors']),290)
  self.assertEqual(m['source_primitive_calls'],192147228)
  self.assertFalse(m['physical_admission']);self.assertFalse(m['actual_installed_engine'])
  self.assertIsNone(m['actual_token_latency_ps'])
if __name__=='__main__':unittest.main()
