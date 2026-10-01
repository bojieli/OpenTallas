import json
import sys
from collections import Counter
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import w19_burst_admission as A


def test_scope_verdict_and_JSON_roundtrip():
    r=A.build()
    assert r['verdict']['credit_450'].startswith('REJECT_AS_VALIDATED_UPPER_BOUND')
    assert r['verdict']['bank_3'].startswith('CONFIRM conditional3cycles')
    assert json.loads(json.dumps(r))==r
    assert r['ceilings']['current_HC_one_line_controller_bytes_s']==153600000000
    assert not r['ceilings']['actual_one_TB_credit']
    assert not r['ready_to_build'] and r['full_token_cycles'] is None


def test_exact0833_tail_is_post_write_not_response():
    r=A.bank_tail()
    assert r['tail_after_bank_write_cycles']==3
    assert r['tail_after_response_accept_cycles']==4


def test_finite_stall_exceeds_450_serial_without_infinite_queue():
    r=A.bank_tail(1024)
    assert r['tail_serial_cycles_ceil']==771
    assert r['tail_serial_cycles_ceil']>450


def test_one_SM_contention_does_not_fit_three_cycle_tail():
    r=A.same_SM_trace()
    assert r['delivered_lines']==32 and r['sectors']==128
    assert r['tail_after_last_bank_write']==31
    assert r['tail_after_last_response_accept']==35


def test_prepared_port_capacity_is_finite_and_atomic():
    m=A.Admission(ports=1,credits=Counter({0:8}))
    first=m.prepare(0,[0]*4,16)
    before=m.credits[0]
    assert m.prepare(16,[0]*4,32) is None
    assert m.credits[0]==before and len(m.pending)==1
    snapshot=m.request(first)
    assert not m.admit([first],[64]*32,controller_ready=False)
    assert m.request(first)==snapshot and not m.pending[first]['issued']


def test_two_overlapping_requests_do_not_double_use_PC_room():
    m=A.Admission(ports=2,credits=Counter({0:8}));rooms=[64]*32
    for pc in range(4):rooms[pc]=4
    tags=[m.prepare(0,[0]*4,16) for _ in range(2)]
    assert m.admit(tags,rooms)==[tags[0]]
    assert m.pending[tags[0]]['issued']
    assert not m.pending[tags[1]]['issued']


def test_two_complementary_groups_jointly_fit():
    m=A.Admission(ports=2,credits=Counter({0:8}))
    tags=[m.prepare(addr,[0]*4,32) for addr in (0,16)]
    assert m.admit(tags,[64]*32)==tags
    assert all(m.pending[t]['issued'] for t in tags)


def test_same_parity_metadata_banks_serialize_without_free_overlap():
    m=A.Admission(ports=2,groups=3,credits=Counter({0:12}))
    even=m.prepare(0,[0]*4,48);odd=m.prepare(16,[0]*4,48)
    assert m.admit([odd],[64]*32)==[odd]
    next_even=m.prepare(32,[0]*4,48)
    assert m.admit([even,next_even],[64]*32)==[even]
    assert not m.pending[next_even]['issued']


def test_duplicate_grant_and_PC_fold_credit_failure_leave_state():
    m=A.Admission(ports=1,credits=Counter({0:4}))
    tag=m.prepare(4092,[0]*4,4108);rooms=[64]*32;rooms[A.M.pc_of(4092)]=4
    assert not m.admit([tag],rooms)
    assert not m.pending[tag]['issued']
    assert m.admit([tag],[64]*32)==[tag]
    with pytest.raises(ValueError):m.admit([tag],[64]*32)


def test_both_granted_bursts_complete_exactly_under_actual_PC_mapping():
    m=A.Admission(ports=2,credits=Counter({0:8}))
    tags=[m.prepare(addr,[0]*4,32) for addr in (0,16)]
    assert m.admit(tags,[64]*32)==tags
    for phase in (2,0,3,1):
        rsp={}
        for g,t in enumerate(tags):
            for line in range(4):
                beat=4*line+phase
                rsp[A.M.pc_of(16*g+beat)]=(t,beat,bytes([16*g+beat])*32,0)
        accepted,_=m.step(rsp);assert len(accepted)==8
    for _ in range(32):m.step()
    assert not m.pending and len(m.ring_lines)==8 and m.credits[0]==0
    for e in m.landing.delivered:
        start=e['tag']*4
        assert e['data']==b''.join(bytes([start+i])*32 for i in range(4))
    for t in list(m.ring_lines):m.consume_SM_line(t)
    assert m.credits[0]==8
