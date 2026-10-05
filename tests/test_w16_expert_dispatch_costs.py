import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w16_expert_dispatch_costs as C


@pytest.fixture
def point():
    return next(c for c in json.loads((C.ROOT/C.GEOMETRY).read_text())['candidates'] if c['q_pairs']==1024)


def service():
    return dict(**{f:1 for f in C.FIELDS},request_queue_data_bits_per_rank_hop=81920,
        return_queue_data_bits_per_rank_hop=20480,request_and_return_share_only_one_credit=False)


def test_actual_known_cost_does_not_become_complete_bound(point):
    r=C.calculate(point,{})
    assert r['known_conditional_partial_fabric_cycles']==606960
    assert r['known_conditional_partial_ns']=='505800'
    assert r['complete_dispatch_bound_ticks'] is None and r['missing_inputs']


def test_finite_credit_held_through_actual_return(point):
    r=C.calculate(point,service())
    assert len(r['trace'])==240
    for a,b in zip(r['trace'],r['trace'][1:]):
        assert b['request_start_tick']>a['response_visible_and_request_credit_release_tick']
    assert not r['physical_admission'] and not r['source_destination_progress_qualified']


def test_four_rank_links_do_not_multiply_single_rank_speed(point):
    s=service();s['zero_proved']={f:True for f in C.FIELDS}
    for f in C.FIELDS:s[f]=0
    assert C.calculate(point,s)['complete_dispatch_bound_ticks']==606960*3


def test_missing_progress_zero_deadlock_and_capacity_refused(point):
    s=service();s['consumer_remainder_ticks']=None
    assert C.calculate(point,s)['complete_dispatch_bound_ticks'] is None
    s=service();s['reverse_CDC_ticks']=0
    assert 'reverse_CDC_ticks' in C.calculate(point,s)['missing_inputs']
    s=service();s['request_and_return_share_only_one_credit']=True
    with pytest.raises(ValueError,match='deadlock'):C.calculate(point,s)
    s=service();s['request_queue_data_bits_per_rank_hop']=81919
    with pytest.raises(ValueError,match='capacity'):C.calculate(point,s)
