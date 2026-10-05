import importlib.util
import json
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('stream',ROOT/'tools/dsrom_s81_level2_service_stream.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

def test_anchor_minimises_rank_sum_not_fragment_max():
    ts=[dict(rank=0,source_stage=3,input_bytes=16,output_bytes=4),
        dict(rank=0,source_stage=4,input_bytes=64,output_bytes=4),
        dict(rank=1,source_stage=3,input_bytes=4,output_bytes=4)]
    assert m.choose_anchor(ts,[3,4])==4

def test_reservation_counts_positions_and_all_no_ready_roots():
    q=[2]*128
    assert sum(m.reserve_before_go(q,6,[12]*128))==1536
    with pytest.raises(ValueError): m.reserve_before_go(q,6,[11]*128)
    with pytest.raises(ValueError): m.reserve_before_go(q,9,[18]*128)

def test_complete_native_shape_required():
    with pytest.raises(ValueError):m.reserve_before_go([1]*64,1,[1]*64)

def test_source_replay_and_no_false_admission():
    r=m.model(ROOT)
    frozen=json.loads((ROOT/'results/uarch/dsrom_s81_level2_service_stream_20261004/model.json').read_text())
    assert r==frozen
    assert len(r['homes'])==40 and len({h['hub_endpoint'] for h in r['homes']})==40
    assert r['homes'][20]['adjacent_field_stage'] in [37,38]
    assert r['field37_38_unchanged'] and r['added_serial_stages']==0
    assert r['cut']['selected_anchor_chain_byte_hops']<r['cut']['old_provider_anchor_chain_byte_hops']
    assert r['cut']['single_user_token_delta_ns'] is None
    assert not r['physical_build_admitted'] and not r['placement']['placed_fit']
    assert not r['endpoints']['result']['retained_source_capture_CAP1_sufficient']
