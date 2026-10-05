from pathlib import Path
import json
import pytest
from tools.gpu_sys.canonical_qwen_native_aperture_model import model, FIELDS, OFF, BITS, WORDS
from tools.gpu_sys.canonical_qwen_native_aperture_rtl import generate
from tools.gpu_sys.canonical_qwen_native_bank_views import generate as bank_generate
from tools.gpu_sys.canonical_qwen_native_aperture_bindings import NativeApertureAuthority
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.h4_qwen_released_provider_delivery import PROGRAM_SHA
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rtl/experimental/canonical_qwen_native_apertures_20261003'


def test_single_record_conservation_and_seal_namespace():
    occupied=set()
    for k,w in FIELDS.items():
        o,ww=OFF[k]; assert w==ww
        for b in range(o,o+w): assert b not in occupied; occupied.add(b)
    assert occupied==set(range(BITS))
    assert BITS==1150 and WORDS==27 and WORDS*44>=BITS
    m=model(); assert m['state']['protected_bits_total']==64*27*72
    assert m['state']['seal_WORD_INDEX_begin']>624
    assert m['source_bank_delta']['additional_physical_FF']==0


def test_generators_reproduce_committed_sources(tmp_path):
    assert generate(tmp_path).read_bytes()==(OUT/'ot_gpu_qwen_native_aperture_collector.sv').read_bytes()
    assert bank_generate(tmp_path).read_bytes()==(OUT/'ot_gpu_qwen_native_aperture_range_owner.sv').read_bytes()


def test_model_regeneration_and_no_unqualified_latency():
    assert model()==json.loads((ROOT/'results/uarch/canonical_qwen_native_apertures_20261003/model.json').read_text())
    m=model(); assert m['full_factory_ready'] is False
    assert m['cost']['loadedSSFFdelay_unknown']
    assert m['cost']['collector_capture_edges_at_most']==7
    assert m['cost']['nonoverlapped_source_query_and_capture_edges_at_most']==32
    assert 'nonoverlapped_added_cycles_upper_bound' not in m['cost']


def test_cursor_is_protected_independent_key_and_positive_advance():
    s=(OUT/'ot_gpu_qwen_native_aperture_collector.sv').read_text()
    assert 'cmd_' not in '\n'.join(l for l in s.splitlines() if not l.strip().startswith('//'))
    assert 'next_c[C_SOURCE_STEP +:6]=cursor_load_step' in s
    assert 'next_c[C_SOURCE_SUBSTEP +:2]=cursor_load_substep' in s
    assert 'c[C_TERMINAL]&&c[C_ADVANCE_PENDING]&&controller_idle&&selected_routes_drained' in s
    assert 'reverse_sequence==c[C_SEQUENCE +:64]' in s
    assert 'terminal_sequence==c[C_SEQUENCE +:64]' in s
    assert 'output_visible&&c[C_TERMINAL]&&!c[C_ADVANCE_PENDING]' in s
    assert 'cursor_load_tail[key_lane*2 +:2]==count[1:0]' in s
    assert 'cursor_load_scalars[key_lane]==(count==1)' in s
    assert 'cursor_load_descriptor<116&&cursor_load_template<13' in s


def test_cursor_close_does_not_clear_source_lease():
    s=(OUT/'ot_gpu_qwen_native_aperture_collector.sv').read_text()
    assert 'source_native_retire' not in s and 'claim_' not in s
    assert '!c[C_LIVE]&&!c[C_CURSOR_LIVE]&&!c[C_ADVANCE_PENDING]&&frame_tuple==' in s
    assert 'cursor_load_sequence!=c[C_SEQUENCE +:64]' in s


def test_persistent_scope_and_typed_workspace_proof():
    s=(OUT/'ot_gpu_qwen_native_aperture_range_owner.sv').read_text()
    assert 'QB=304' in s and 'Q_WORKSPACE=303' in s
    assert 'claim_ready=active&&claim_legal&&claim_match<0&&empty_row>=0&&!b[B_LIVE]&&!q[Q_LIVE]' in s
    assert 'r[release_row][R_CONSUMER_COUNT +:9]&&!q[Q_LIVE]&&!b[B_LIVE]' in s
    assert 'lease_scope_workspace=lease_scope_valid&&workspace_held_valid&&native_rf_workspace_free' in s
    assert 'query_slot<10&&query_version==2047' in s
    assert 'saved_workspace?11\'d2047' in s
    assert 'query_workspace?issuer_held_owner55[54:9]' in s


class Root:
    def __init__(self): self.edges=0; self.writes=[]
class Pin:
    def __init__(self,root,index,enabled=1): self.root=root; self.index=index; self.enabled=enabled; self.values={}
    def parameter(self,k): return self.enabled if k=='ENABLE' else self.index
    def get(self,k): return self.values.get(k,0)
    def set(self,k,v): self.root.writes.append((self.index,k,v)); self.values[k]=v
    def settle(self): pass
    def tick(self): self.root.edges+=1
class Authority:
    def __init__(self,root):
        self.owners=[type('Owner',(),dict(physical=Pin(root,i)))() for i in range(64)]
        self.RF=[type('RF',(),dict(ports=Pin(root,i)))() for i in range(64)]
    def native_binding(self,*a): raise TransportError('actual command provider absent')


def enrolled():
    root=Root(); collectors=[Pin(root,i) for i in range(64)]
    a=NativeApertureAuthority(Authority(root),collectors)
    return root,collectors,a


def test_constructor_no_clock_no_pinwrite_no_fake_command_provider():
    root,_,a=enrolled(); assert root.edges==0 and root.writes==[]
    with pytest.raises(TransportError,match='provider absent'): a.native_binding('native_primitive_RF',{})


@pytest.mark.parametrize('fault',['fault','issuer_held_fault'])
def test_actor_selection_refuses_actual_fault(fault):
    _,p,a=enrolled(); p[17].values.update(issuer_held_valid=1,issuer_held_tuple=(5<<164)|(17<<30),issuer_held_owner=55)
    p[17].values[fault]=1
    with pytest.raises(TransportError,match='fault'):a._actor(dict(program_sha256=PROGRAM_SHA,source_PC=5))


def test_actor_selection_from_hardware_not_request_echo():
    root,p,a=enrolled(); t=(5<<164)|(17<<30)
    p[17].values.update(issuer_held_valid=1,issuer_held_tuple=t,issuer_held_owner=999)
    got=a._actor(dict(program_sha256=PROGRAM_SHA,source_PC=5,actor=0,tuple239=0,owner55=0))
    assert got==(17,p[17],t,999) and root.edges==0 and root.writes==[]
    with pytest.raises(TransportError):a._actor(dict(program_sha256=PROGRAM_SHA,source_PC=6))


def test_no_multiple_actor_or_missing_scope_fallback():
    _,p,a=enrolled(); r=dict(program_sha256=PROGRAM_SHA,source_PC=5)
    with pytest.raises(TransportError):a._actor(r)
    for i in (2,17):p[i].values.update(issuer_held_valid=1,issuer_held_tuple=(5<<164)|(i<<30))
    with pytest.raises(TransportError,match='one actual'):a._actor(r)


def test_compiled_native_RF_reservation_is_outside_all_published_homes():
    from tools.gpu_sys.canonical_qwen_source_mapping import SourcePlacement
    p=SourcePlacement.released()
    assert len(p.rf)==26624
    assert min(h.first for h in p.rf.values())>=32
    # Reservation does not prove TC/private-RF idle: actual signal is required.
    assert 'native_rf_workspace_free' in (OUT/'ot_gpu_qwen_native_aperture_range_owner.sv').read_text()
