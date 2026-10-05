"""Actual installed collector/INITIAL components on the ONE enclosing clock.

Only source-owned cursor/capture/INITIAL offers are host writable. Physical
profile/controller observations are read-only and require actual source joins.
"""
from tools.gpu_sys.canonical_qwen_transport import TransportError
class NativeAperturePorts:
 def __init__(self,root,index):
  if type(index)is not int or not 0<=index<64:raise TransportError('actor0..63')
  self.root,self.index=root,index
  c=root.book.get('native_aperture_contract',{})
  if c.get('actual_module')!='ot_gpu_qwen_native_aperture_collector' or c.get('collector_count')!=64:
   raise TransportError('actual installed64 collector source required')
  if root.get('native_apertures_enabled')!=1:raise TransportError('compiled collector optin disabled')
 def parameter(self,n):
  if n=='ENABLE':return self.root.get('native_apertures_enabled')
  if n=='ACTOR_INDEX':return self.index
  raise TransportError('unknown collector parameter')
 def _pin(self,n):
  key='native_aperture_'+n;p=self.root.book.get('pins',{}).get(key)
  if not p or p.get('block')!='native_aperture' or p.get('count')!=64:raise TransportError('actual actor collector pin '+n)
  return key,p
 def get(self,n):
  key,p=self._pin(n);w=p['leaf_bits'];return (self.root.get(key)>>(self.index*w))&((1<<w)-1)
 def set(self,n,v):
  key,p=self._pin(n);w=p['leaf_bits']
  if p['direction']!='input' or not p.get('host_writable'):raise TransportError('physical observation/held authority is read-only')
  if type(v)is not int or not 0<=v<(1<<w):raise TransportError('source offer width')
  with self.root.lock:
   old=self.root.get(key);mask=((1<<w)-1)<<(self.index*w);self.root.set(key,(old&~mask)|(v<<(self.index*w)))
 def tick(self):return self.root.tick()
 def settle(self):return self.root.settle()

class NativeInitialPorts:
 def __init__(self,root):
  self.root=root
  if root.get('native_apertures_enabled')!=1:raise TransportError('actual INITIAL optin disabled')
  for n in ('busy','fault','go_ready','event_tuple','event_owner'):
   if 'native_initial_'+n not in root.book.get('pins',{}):raise TransportError('actual INITIAL endpoint missing')
 def parameter(self,n):
  if n=='ENABLE':return self.root.get('native_apertures_enabled')
  raise TransportError('unknown INITIAL parameter')
 def _pin(self,n):
  key='native_initial_'+n;p=self.root.book.get('pins',{}).get(key)
  if not p or p.get('block')!='native_initial':raise TransportError('actual INITIAL pin '+n)
  return key,p
 def get(self,n):key,_=self._pin(n);return self.root.get(key)
 def set(self,n,v):
  key,p=self._pin(n)
  if not p.get('host_writable'):raise TransportError('INITIAL event/receipt is read-only')
  if type(v)is not int or not 0<=v<(1<<p['bits']):raise TransportError('INITIAL width')
  return self.root.set(key,v)
 def tick(self):return self.root.tick()
 def settle(self):return self.root.settle()
