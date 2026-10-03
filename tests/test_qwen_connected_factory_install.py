"""New integration behavior only; never launches or repeats an RTL gate."""
import hashlib
import io
import json
from pathlib import Path
from unittest.mock import patch
import pytest
from tools.qwen_connected_service_install import ROOT
from tools.gpu_sys.canonical_qwen_installed_services import installed_scratch_pins_class
from tools.gpu_sys.canonical_qwen_scratch_simulator import ScratchComponentPins, ALIASES, SharedEdgeServices
from tools.gpu_sys.canonical_qwen_transport import TransportError

OUT=ROOT/'rtl/model/qwen_hbm_connected_factory_20261003'


def test_one_real_owned_mux_and_source_owner_with_pinned_dependencies():
    book=json.loads((OUT/'ports.json').read_text())
    top=(OUT/'ot_gpu_qwen_hbm_integrated_scratch.sv').read_text()
    assert book['top']=='ot_gpu_qwen_hbm_integrated_scratch'
    assert book['inventory']['source_owner_count']==64
    assert top.count('begin:g_source_owner')==1
    assert top.count('ot_gpu_qwen_scratch_client_mux #')==1
    assert 'ENABLE_SCRATCH_CLIENT=0' in top
    assert 'source_owner_page_ack_valid[i]=sm_rf_ack_accept[i]' in top
    assert book['pins']['issuer_rf_range_ack_valid']['direction']=='output'
    for p,h in book['source_sha256'].items():
        assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    deps=(OUT/'sources.f').read_text().splitlines()
    assert all((ROOT/p).is_file() for p in deps)
    assert sum(p.endswith('ot_gpu_qwen_scratch_client_mux.sv') for p in deps)==1


def test_real_scratch_and_owner_components_share_root_and_never_tick():
    Pins=installed_scratch_pins_class()
    reply='ot_gpu_qwen_hbm_integrated_scratch ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128 SCRATCH_CLIENT=1\n'
    writer=io.StringIO()
    root=Pins(io.StringIO(reply),writer,portbook=OUT/'ports.json')
    assert writer.getvalue()=='HELLO\n'
    owner=root.component('source_owner',63)
    scratch=root.component('scratch',63,aliases=ALIASES)
    assert isinstance(scratch,ScratchComponentPins)
    assert scratch.root is owner.root is root
    assert root.edges==0 and root.hooks==[]
    assert owner._pin('query_tuple')[2]==239
    assert scratch._pin('wdata')[0]=='scratch_client_wdata'
    assert scratch._pin('wdata')[1]['direction']=='input'
    assert root._pin('sm_scratch_wdata')['direction']=='output'


def test_old_ranked_binary_never_qualifies_owned_scratch_sourcebook():
    Pins=installed_scratch_pins_class()
    old='ot_gpu_qwen_hbm_integrated_ranked ENABLE=1 SM=64 W2=256 RANKS=2 PC_PER_RANK=128\n'
    with pytest.raises(TransportError):Pins(io.StringIO(old),io.StringIO(),portbook=OUT/'ports.json')


def test_observer_wraps_actual_payload_plus_matrix_group_without_second_clock():
    import sys
    sys.path.insert(0,str(ROOT/'tools'))
    from w2_fullnc6_run import observe_registered_payload
    from types import SimpleNamespace
    events=[]
    def service(name):
        return SimpleNamespace(before_edge=lambda:events.append(name+' before'),after_edge=lambda:events.append(name+' after'))
    payload=service('payload');matrix=service('matrix');observer=service('observer')
    group=SharedEdgeServices(payload,[matrix])
    root=SimpleNamespace(hooks=[group],edge_open=False,stopped=False)
    observe_registered_payload(root,group,observer)
    root.hooks[0].before_edge();events.append('one actual edge');root.hooks[0].after_edge()
    assert events==['payload before','matrix before','observer before','one actual edge',
                    'payload after','matrix after','observer after']
    assert len(root.hooks)==1
    with pytest.raises(ValueError):observe_registered_payload(root,group,observer)
