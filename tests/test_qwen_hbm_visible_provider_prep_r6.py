import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_visible_provider_prep_r6 import VisibleProvider,Beat,source_timing,derive

def beat(tag,addr=0):return Beat(addr,tag,100+tag,200+tag,write=True,data=tag+1)

def test_finite_capacity_before_column_and_pop():
    p=VisibleProvider(source_timing())
    for i in range(4):assert p.reserve(beat(i,i),0)
    assert not p.reserve(beat(4,4),0)
    with pytest.raises(ValueError,match='reserve before'):p.column(beat(4,4),10000)
    assert len(p.slots)==4

def test_full_address_RAW_delayed_visibility():
    t=source_timing();p=VisibleProvider(t);a=beat(0,0);b=beat(1,1<<32)
    assert p.reserve(a,0) and p.reserve(b,0)
    p.column(a,10000);p.column(b,10000)
    due=10000+t['CWL_PS']+t['BURST_PS']
    assert p.read(0,due-1) is None and p.read(1<<32,due-1) is None
    assert p.read(0,due)==1 and p.read(1<<32,due)==2

def test_immutable_held_and_credit_retained_until_reverse():
    t=source_timing();p=VisibleProvider(t);a=beat(0)
    p.reserve(a,0);p.column(a,10000);due=10000+t['CWL_PS']+t['BURST_PS']
    held=p.offer(due);assert p.capture(due,False) is None
    assert p.offer(due+50000)==held
    assert p.capture(due+50000,True)==held and len(p.slots)==1
    with pytest.raises(ValueError,match='lifecycle'):p.downstream(a,'reverse_credit')
    for event in ['forward_CDC','completion_store','consumer_retire','reverse_credit']:p.downstream(a,event)
    assert p.drained()

def test_causal_column_and_same_address_residence():
    p=VisibleProvider(source_timing());a=beat(0)
    assert p.reserve(a,0)
    assert not p.reserve(beat(1),0)
    with pytest.raises(ValueError,match='causal'):p.column(a,9999)

def test_actual_reorders_price_frozen_35_edges_and_costs():
    m=derive()
    assert [r['selected_index'] for r in m['actual_reorder_stage_costs']]==[15,15]
    assert [r['scan_shift_edges'] for r in m['actual_reorder_stage_costs']]==[35,35]
    assert m['actual_reorder_stage_costs'][0]['isolated_reservation_ready_ps']==107000
    assert m['address_residence']['address_span_bytes']==1<<39
    assert m['additional_to_r1_control']['total_bits']>100000
    assert not m['hardware_build_ready'] and not m['provider_PASS']


def test_same_key_cannot_mutate_reserved_address_or_data():
    from dataclasses import replace
    p=VisibleProvider(source_timing());a=beat(0);p.reserve(a,0)
    with pytest.raises(ValueError,match='immutable'):p.column(replace(a,addr=1),10000)


def test_source_tail_and_parent_independent_witness_binding():
    m=derive()
    assert m['parent_independent_witness']['all_artifact_hashes_match']
    assert m['known_visibility_tail_ps']==7274
    assert [r['elapsed_ps'] for r in m['actual_WR_bound_comparisons']]==[0,0,0,0,625,101]
    assert [r['early_by_ps'] for r in m['actual_WR_bound_comparisons']]==[7274,7274,7274,7274,6649,7173]
