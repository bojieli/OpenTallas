"""Enroll real TC/scratch services in the existing connected factory clock.

Providers are released physical owners, not host arithmetic or allocation maps.
No constructor ticks, resets, lease defaults, synthetic completion or second hook.
"""
from tools.gpu_sys import canonical_qwen_matrix_tc_pins as T
from tools.gpu_sys import canonical_qwen_matrix_padding as P
from tools.gpu_sys import canonical_qwen_matrix_scratch_adapter as A
from tools.gpu_sys import canonical_qwen_matrix_services as S
from tools.gpu_sys import canonical_qwen_service_calendar as C
from tools.gpu_sys.canonical_qwen_scratch_simulator import ALIASES

class InstalledTCPins(T.TCPins):
 def __init__(self,root,rank,SM,*,enabled=False):
  super().__init__(root,rank,SM,enabled=enabled)
  C.need(root.get('tc_enabled')==1,'actual compiled TC opt-in must be enabled')

class SharedConsumption(T.ConsumptionAuthority):
 def before_edge(self):
  # SET does not evaluate the model. Sample consumption only after all current
  # offers have settled, before the ONE common physical edge owned by root.
  self.TC.root.settle()
  super().before_edge()

class MatrixFactory:
 def __init__(self,root,providers,native,*,enabled=False):
  C.need(enabled and type(providers) is dict and bool(providers),'actual physical MATRIX providers, default off')
  self.root=root;self.native=native;self.bindings={};self.active={}
  C.need(root.book['inventory'].get('source_owner_count')==64
         and root.book['inventory'].get('native_TC_count')==64,'installed complete source owners and genuine TCs')
  for key,provider in providers.items():
   C.need(type(key) is tuple and len(key)==2,'explicit actual execution rank/SM')
   rank,SM=key;p=InstalledTCPins(root,rank,SM,enabled=True)
   C.need(all(callable(getattr(provider,n,None)) for n in S.MatrixPhysicalServices.REQUIRED),
          'all original actual hardware input/output provider methods required')
   wrapped=SharedConsumption(provider,p)
   scratch=root.component('scratch',rank*32+SM,aliases=ALIASES)
   service=A.MatrixPhysicalServices(wrapped,scratch,enabled=True)
   self.bindings[key]=(p,wrapped,service)
 @property
 def matrix_services(self):return tuple(s for p,a,s in self.bindings.values())
 def controller(self,source_PC,rank,SM):
  key=(rank,SM);C.need(key in self.bindings,'source-assigned physical context, no rank modulo SM')
  C.need(key not in self.active or self.active[key].phase=='done','finite physical context still owned')
  p,a,s=self.bindings[key]
  C.need(getattr(s,'installed',False),'existing connected factory must enroll shared service hook first')
  c=P.MatrixOperatorController(p,s,self.native,source_PC,enabled=True)
  self.active[key]=c;return c
 def enroll(self,build_factory,authority,native_handlers,w2_ports,*,enabled=False):
  """Call Russell/Euclid actual build function, preserving its single hook.

  Caller passes the installed full native four handlers. No protocol controls
  or selected primitive fixture stand in for the full native dispatcher.
  """
  C.need(enabled and callable(build_factory),'actual installed connected builder required')
  C.need(not self.root.hooks,'no duplicate shared-edge enrollment')
  result=build_factory(self.root,authority,native_handlers,w2_ports,
                       matrix_services=self.matrix_services,enabled=True)
  C.need(len(self.root.hooks)==1 and all(s.installed for s in self.matrix_services),
         'ONE shared physical edge with real matrix services')
  result['matrix_factory']=self;return result
