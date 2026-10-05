"""Actual scratch-client successor API. Never drives readonly SM/router aliases.
Workspace/offer identity are physical Nash inputs, not host allocation success.
"""
import json
from pathlib import Path
from tools.gpu_sys.canonical_qwen_ranked_simulator import RankedEnclosingPins,RankedComponentPins,build as build_ranked
from tools.gpu_sys.canonical_qwen_simulator import EnclosingPins
from tools.gpu_sys.canonical_qwen_transport import TransportError
PORTBOOK=Path(__file__).resolve().parents[2]/'rtl/model/qwen_hbm_integrated_20261003/scratch/ports.json'
ALIASES={n:'client_'+n for n in ('valid','write','addr','wdata','ready','done','done_ready','rdata')}
class ScratchEnclosingPins(RankedEnclosingPins):
 def __init__(self,reader,writer,*,portbook=PORTBOOK):
  # Reuse source-selected synchronous transport, replace only compiled topology.
  import threading
  self.reader,self.writer=reader,writer;self.book=json.loads(Path(portbook).read_text())
  self.hooks=[];self.edge_open=self.stopped=False;self.edges=0;self.lock=threading.RLock()
  hello=self._rpc('HELLO')
  if hello!='ot_gpu_qwen_hbm_integrated_scratch ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128 SCRATCH_CLIENT=1':
   self.stopped=True;raise TransportError('actual scratch successor topology/optin differs: '+hello)
 def component(self,block,index=0,*,rank=None,aliases=None):
  if block=='scratch':
   if rank is not None:raise TransportError('scratch uses actual flat execution rank*32+SM')
   return ScratchComponentPins(self,index,aliases=aliases)
  return super().component(block,index,rank=rank,aliases=aliases)
class ScratchComponentPins(RankedComponentPins):
 def __init__(self,root,index,*,aliases=None):
  if type(index) is not int or not 0<=index<64:raise TransportError('actual scratch instance')
  self.root,self.block,self.index=root,'scratch',index;self.aliases=dict(aliases or {})
 def parameter(self,name):
  if name=='ENABLE_CLIENT':return 1
  if name=='INDEX':return self.index
  raise TransportError('unknown actual scratch parameter '+name)
def scratch_component(pins,rank,SM):
 if not isinstance(pins,ScratchEnclosingPins) or type(rank) is not int or rank not in (0,1) or type(SM) is not int or not 0<=SM<32:
  raise TransportError('captured actual execution rank/SM required')
 return pins.component('scratch',rank*32+SM,aliases=ALIASES)
class SharedEdgeServices:
 def __init__(self,payload,services):self.payload=payload;self.services=tuple(services)
 def before_edge(self):
  self.payload.before_edge()
  for s in self.services:s.before_edge()
 def after_edge(self):
  self.payload.after_edge()
  for s in self.services:s.after_edge()
def build(pins,authority,native_handlers,w2_ports,*,matrix_services,enabled=False):
 # Services are supplied by the real native factory after physical binding,
 # never manufactured from a reservation, range dictionary or omitted callback.
 if not enabled or not isinstance(pins,ScratchEnclosingPins):raise TransportError('scratch factory defaultoff')
 services=tuple(matrix_services)
 if not services:raise TransportError('actual native MATRIX services required; no fallback')
 from tools.gpu_sys.canonical_qwen_matrix_services import MatrixPhysicalServices
 seen=set()
 for s in services:
  if not isinstance(s,MatrixPhysicalServices):raise TransportError('actual physical MATRIX service required')
  p=s.scratch.p
  if not isinstance(p,ScratchComponentPins) or p.root is not pins or p.aliases!=ALIASES or p.index in seen:
   raise TransportError('one owned actual scratch client per captured execution context')
  if getattr(s,'installed',False):raise TransportError('service already owns an edge hook')
  seen.add(p.index)
 result=build_ranked(pins,authority,native_handlers,w2_ports,enabled=True)
 # Existing build enrolls one payload hook. Replace that one enrollment with
 # its literal group BEFORE traffic, never tick/reset or enroll a second clock.
 if len(pins.hooks)!=1 or pins.hooks[0] is not result['payload'] or pins.edge_open:
  raise TransportError('actual single shared hook enrollment changed')
 pins.hooks[0]=SharedEdgeServices(result['payload'],services)
 for s in services:s.installed=True
 result['matrix_services']=services
 return result
