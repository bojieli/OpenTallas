"""Interface checks for the connected install; no RTL gate or host grants."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tools.gpu_sys.canonical_qwen_installed_services import (InstalledServicePins,
    scratch_component, SourceOwnerPins)
from tools.gpu_sys.canonical_qwen_transport import TransportError
from tools.qwen_connected_service_install import ROOT, OUT, MODEL, FROM, TO


def test_installed_owner_events_and_issuer_wires():
    book=json.loads((OUT/'ports.json').read_text())
    sv=(OUT/'ot_gpu_qwen_hbm_integrated_ranked.sv').read_text()
    cpp=(OUT/'pin_driver.cpp').read_text()
    assert book['inventory']['source_owner_count']==64
    assert sv.count('begin:g_source_owner')==1
    for name in FROM:
        assert book['pins']['source_owner_'+name]['direction']=='output'
        assert 'if(name=="source_owner_'+name+'"){auto v=' not in cpp
    for name, dest in TO.items():
        assert book['pins'][dest]['direction']=='output'
        assert 'if(name=="'+dest+'"){auto v=' not in cpp
        assert '.%s(source_owner_%s[' % (name,name) in sv
    assert 'issuer_backend_go_valid[i] && issuer_backend_go_ready[i]' in sv
    assert '.page_ack_valid(source_owner_page_ack_valid[i])' in sv
    assert 'source_owner_page_ack_valid[i]=sm_rf_ack_accept[i]' in sv


def test_frame_and_output_lifetime_are_separate_real_ports():
    book=json.loads((OUT/'ports.json').read_text())
    assert book['pins']['source_owner_frame_retire_valid']['direction']=='output'
    assert book['pins']['source_owner_source_native_retire_valid']['direction']=='input'
    assert book['pins']['source_owner_claim_valid']['direction']=='input'
    assert book['pins']['source_owner_bind_valid']['direction']=='input'
    assert book['pins']['source_owner_allcopies_fenced']['direction']=='input'
    # Installation never invokes warm/cold reset, grants, or provider fences.
    assert not json.loads(MODEL.read_text())['fullbuild_ready']


def test_pinned_originals_and_actual_sourcebook():
    model=json.loads(MODEL.read_text())
    for path,digest in model['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    book=json.loads((OUT/'ports.json').read_text())
    for path,digest in book['source_sha256'].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest
    deps=(OUT/'sources.f').read_text().splitlines()
    assert all((ROOT/p).is_file() for p in deps)
    assert sum(p.endswith('ot_gpu_qwen_native_range_owner.sv') for p in deps)==1


def test_all_actual_owner_indices_without_clock_or_construction_grants():
    book=json.loads((OUT/'ports.json').read_text())
    root=SimpleNamespace(book=book,_pin=lambda n:book['pins'][n])
    for i in range(64):
        p=SourceOwnerPins(root,i)
        assert p.parameter('ENABLE')==1 and p.parameter('SM_INDEX')==i
        assert p._pin('query_tuple')[0]=='source_owner_query_tuple'
        assert p._pin('query_tuple')[2]==239


@pytest.mark.parametrize('rank,sm',[(0,0),(0,31),(1,0),(1,31)])
def test_scratch_uses_only_installed_protected_client(rank,sm):
    calls=[]
    widths=dict(valid=1,write=1,addr=10,wdata=512,ready=1,done=1,done_ready=1,rdata=512)
    inputs={'valid','write','addr','wdata','done_ready'}
    def pin(name):
        assert name.startswith('scratch_client_')
        n=name.removeprefix('scratch_client_')
        return dict(bits=64*widths[n],direction='input' if n in inputs else 'output')
    sentinel=object()
    from tools.gpu_sys.canonical_qwen_scratch_simulator import ScratchEnclosingPins, ALIASES
    root=ScratchEnclosingPins.__new__(ScratchEnclosingPins)
    root._pin=pin
    root.component=lambda block,i,**kw: calls.append((block,i,kw)) or sentinel
    assert scratch_component(root,rank,sm) is sentinel
    assert calls==[('scratch',rank*32+sm,{'aliases':ALIASES})]


def test_missing_scratch_mux_refuses_before_any_component_or_edge():
    book=json.loads((OUT/'ports.json').read_text())
    def pin(name):
        if name not in book['pins']:raise TransportError('unconnected actual pin')
        return book['pins'][name]
    root=SimpleNamespace(_pin=pin,component=lambda *args:pytest.fail('must not bind raw scratch'))
    with pytest.raises(TransportError):scratch_component(root,1,31)


def test_scratch_output_direction_cannot_be_forged_as_client_input():
    root=SimpleNamespace(_pin=lambda n:dict(bits=64,direction='output'))
    with pytest.raises(TransportError):scratch_component(root,0,0)


@pytest.mark.parametrize('rank,sm',[(True,0),(0,True),(2,0),(0,32)])
def test_bad_captured_location_refuses(rank,sm):
    with pytest.raises(TransportError):scratch_component(None,rank,sm)
