from pathlib import Path
import json
import pytest
from tools.gpu_sys.canonical_qwen_manifest_range_owner import profiles
from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
from tools.gpu_sys.canonical_qwen_manifest_owner_bindings import PhysicalManifestSourceAuthority
from tools.gpu_sys.canonical_qwen_transport import TransportError
ROOT=Path(__file__).resolve().parents[1]

@pytest.fixture(scope='module')
def placement():return SourcePlacement.released()


def test_complete_profile_conserves_every_actual_RF_home(placement):
 ins,outs=profiles(placement)
 assert sum(map(len,outs.values()))==sum(h.birth>=0 for h in placement.rf.values())
 assert sum(map(len,ins.values()))==sum(len(h.consumers) for h in placement.rf.values())
 for h in placement.rf.values():
  sm=h.rank*32+h.sm;v=placement.version_ids[h.version]
  if h.birth>=0:assert v in outs[sm,h.birth]
  for pc in h.consumers:assert v in ins[sm,pc]
 assert max(map(len,ins.values()))==max(map(len,outs.values()))==3


def test_canonical_multiple_and_zero_outputs_not_firstonly(placement):
 ins,outs=profiles(placement)
 assert len(outs[0,5])==3 and len(outs[0,14])==2
 assert not outs.get((0,10)) and not outs.get((0,11))
 assert len(ins[0,4])==2 and len(ins[0,10])==3


def test_INITIAL_command_never_aliases_actual_native_opcode(placement):
 a=object.__new__(PhysicalManifestSourceAuthority);a.placement=placement
 with pytest.raises(TransportError):a._association({'source_PC':-1,'source_key':['RF',0,0,0],'version':'unbound'})
 h=next(h for h in placement.rf.values() if h.birth>=0 and h.rank==0 and h.sm==0)
 with pytest.raises(TransportError):a._association({'source_PC':-1,'source_key':['RF',0,0,h.first],'version':h.version})


def test_no_RF_page_for_arbitrary_native_producer_or_consumer(placement):
 a=object.__new__(PhysicalManifestSourceAuthority);a.placement=placement
 h=next(h for h in placement.rf.values() if h.birth==2 and h.rank==0 and h.sm==0)
 r={'source_PC':1,'source_key':['RF',0,0,h.first],'version':h.version}
 with pytest.raises(TransportError):a.resolve_source(r,True)
 with pytest.raises(TransportError):a.resolve_source(r,False)


def test_witness_is_read_from_installed_hardware_not_a_callback():
 a=object.__new__(PhysicalManifestSourceAuthority)
 class Port:
  def settle(self):pass
  def get(self,n):return dict(fault=0,workspace_held_valid=1,workspace_held_tuple=19,workspace_held_owner55=7,workspace_new_admit=0)[n]
 class Owner:physical=Port()
 a.owners=[Owner()]
 assert a.workspace_view(0)==dict(tuple239=19,owner55=7,new_admit=False)
