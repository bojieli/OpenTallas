"""Views of Pauli's installed controller API on the enclosing clock.
No allocation, grant, source metadata, profile validity, or extra clock owner.
"""
from tools.gpu_sys.canonical_qwen_transport import TransportError

class NativeControllerPorts:
 def __init__(self,root,index):
  c=root.book.get('native_controller_contract',{})
  if type(index)is not int or not 0<=index<64 or c.get('actual_module')!='ot_gpu_native_primitive_controller_authority' or c.get('count')!=64:
   raise TransportError('actual installed native controller source required')
  if root.get('native_apertures_enabled')!=1:raise TransportError('native controller disabled')
  self.root,self.index=root,index
 def parameter(self,n):
  if n=='ENABLE':return self.root.get('native_apertures_enabled')
  if n=='PROGRAM_SHA':return int(self.root.book['native_controller_contract']['PROGRAM_SHA'],16)
  if n=='EXTERNAL_OPCODE_MASK':return self.root.book['native_controller_contract']['external_opcode_mask']
  raise TransportError('unknown controller parameter')
 def _pin(self,n):
  k='native_controller_'+n;p=self.root.book['pins'].get(k)
  if not p or p.get('block')!='native_controller' or p.get('count')!=64:raise TransportError('actual native controller pin '+n)
  return k,p
 def get(self,n):
  k,p=self._pin(n);w=p['leaf_bits'];return (self.root.get(k)>>(self.index*w))&((1<<w)-1)
 def set(self,n,v):
  k,p=self._pin(n);w=p['leaf_bits']
  if p['direction']!='input' or not p.get('host_writable') or type(v)is not int or not 0<=v<(1<<w):raise TransportError('command/accept input width or direction')
  with self.root.lock:
   old=self.root.get(k);mask=((1<<w)-1)<<(self.index*w);self.root.set(k,(old&~mask)|(v<<(self.index*w)))
 def tick(self):return self.root.tick()
 def settle(self):return self.root.settle()
