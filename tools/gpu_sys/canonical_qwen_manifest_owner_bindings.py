"""Physical manifest authority: preserve native PCs and explicit INITIAL class.

`source_PC=-1` is accepted ONLY for an immutable initial home and matches the
reserved INITIAL command239 PC2047. This is a reversible typed command, not
masked/truncated native opcode0. Enclosing initializer is still required.
"""
from tools.gpu_sys.canonical_qwen_range_owner_bindings import PhysicalRangeSourceAuthority
from tools.gpu_sys.canonical_qwen_transport import TransportError

class PhysicalManifestSourceAuthority(PhysicalRangeSourceAuthority):
 def _association(self,request):
  pc=request.get('source_PC')
  if pc==-1:
   key=request.get('source_key')
   if not isinstance(key,list) or len(key)!=4:raise TransportError('INITIAL source key')
   h=self.placement.rf.get((request.get('version'),key[1],key[2]))
   if h is None or h.birth!=-1:raise TransportError('INITIAL is not a native PC alias')
   typed=dict(request,source_PC=2047)
   return super()._association(typed)
  return super()._association(request)

 def resolve_source(self,request,write):
  key=request.get('source_key')
  if not isinstance(key,list) or len(key)!=4:raise TransportError('source key')
  h=self.placement.rf.get((request.get('version'),key[1],key[2]))
  if h is None or (write and request.get('source_PC')!=h.birth) or (not write and request.get('source_PC') not in h.consumers):
   raise TransportError('source producer/consumer opcode outside canonical role')
  return super().resolve_source(request,write)

 def workspace_view(self,index):
  p=self.owners[index].physical;p.settle()
  if p.get('fault') or not p.get('workspace_held_valid'):
   return None
  # Observations only. No grant/capture/retirement is created by this mapping.
  return dict(tuple239=p.get('workspace_held_tuple'),owner55=p.get('workspace_held_owner55'),
              new_admit=bool(p.get('workspace_new_admit')))


def build_RF_authority(pins,placement):
 return PhysicalManifestSourceAuthority(pins,placement)
