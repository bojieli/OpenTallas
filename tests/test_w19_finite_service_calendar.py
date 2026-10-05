from fractions import Fraction
from pathlib import Path
import sys
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_finite_service_calendar as C


def test_phase_edges_and_both_cdc_directions_nonzero():
    assert C.cdc(Fraction(0),C.SLOW)==3*C.SLOW
    assert C.cdc(3*C.SLOW,C.FAST)>3*C.SLOW


def test_all_32_pc_collision_finite_backpressure_and_no_lost_sector():
    events=[dict(return_ps=0,pc=i,client=0,sector=0,tag=i) for i in range(32)]
    r=C.read_calendar(events,1,{0:4})
    assert len(r['timeline'])==32
    assert len({x['crossbar_grant_ps'] for x in r['timeline']})==32
    assert Fraction(r['done_ps'])>32*C.FAST
    assert not r['physical_admission'] and r['full_token_cycles'] is None


def test_controller_byte_budget_not_32pc_free_bandwidth():
    events=[dict(return_ps=0,pc=i,client=i,sector=0,tag=i) for i in range(32)]
    r=C.read_calendar(events,32,{i:1 for i in range(32)})
    assert len({x['crossbar_grant_ps'] for x in r['timeline']})==2


def test_finite_pc_depth_holds_backend_valid():
    events=[dict(return_ps=0,pc=0,client=0,sector=0,tag=i) for i in range(6)]
    r=C.read_calendar(events,1,{0:10})
    assert any(Fraction(x['input_backpressure_ps'])>C.FAST for x in r['timeline'])


def test_missing_consumer_or_backend_event_fails_closed():
    with pytest.raises(ValueError):C.read_calendar([],1,{})
    with pytest.raises(ValueError):C.read_calendar([dict(pc=0,client=0)],1,{0:1})
    with pytest.raises(ValueError):C.write_calendar([dict(submit_ps=0,sector=0,tag=0)],1)


def test_actual_visible_event_and_retained_credit_no_timer_ack():
    e=dict(submit_ps=0,column_ps=10000,visible_ps=17274,sector=0,tag=0)
    r=C.write_calendar([e],2)['timeline'][0]
    assert Fraction(r['credit_and_lock_release_ps'])>Fraction(r['consumer_complete_ps'])>17274
    e['visible_ps']=17273
    with pytest.raises(ValueError,match='visibility'):C.write_calendar([e],2)


def test_fifth_write_cannot_ignore_four_reserved_credits():
    events=[dict(submit_ps=0,column_ps=10000+i*1000,visible_ps=20000+i*1000,sector=i,tag=i) for i in range(5)]
    with pytest.raises(ValueError,match='precedes issue'):C.write_calendar(events,10)


def test_rmw_actual_read_merge_required():
    e=dict(submit_ps=0,column_ps=20000,visible_ps=28000,sector=0,tag=0,partial=True)
    with pytest.raises(ValueError,match='read/merge'):C.write_calendar([e],1)
    e.update(read_return_ps=10000,merge_done_ps=11000)
    assert len(C.write_calendar([e],1)['timeline'])==1


def test_extra_credits_are_not_silently_enabled():
    with pytest.raises(ValueError,match='separate candidate'):C.read_calendar([],1,{0:1},output_depth=4)


def test_four_stack_same_bank_reservation_covers_route_and_consumer():
    events=[dict(return_ps=0,stack=s,pc=i,client=0,sector=0,tag=i) for s in range(4) for i in range(2)]
    rows=C.read_calendar(events,1,{0:1})['timeline']
    assert len(rows)==8
    assert Fraction(rows[2]['crossbar_grant_ps'])-Fraction(rows[0]['crossbar_grant_ps'])>=5*C.FAST


def test_burst_tag_can_deliver_different_sectors_but_not_duplicate():
    events=[dict(return_ps=0,pc=0,client=0,sector=i,tag=1) for i in range(4)]
    assert len(C.read_calendar(events,1,{0:1})['timeline'])==4
    with pytest.raises(ValueError,match='duplicate'):C.read_calendar([events[0],events[0]],1,{0:1})
