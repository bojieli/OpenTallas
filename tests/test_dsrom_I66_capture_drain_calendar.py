import sys
from pathlib import Path
from fractions import Fraction
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_drain_calendar as D
CTX=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=7,user=3,xversion=52,pc=66)
def args():
    # Software test schedule, not selected silicon cadence or actual runtime.
    # Stream period3, serial period4: caller must supply the true phase.
    return dict(ctx=CTX,rows={r:(r%256)//2 for r in range(576)},raw={r:r for r in range(576)},
        capacity=8,issue_edges=range(0,6000,3),return_delays={0:9,1:12},
        consumer_edges=range(2,7000,4),visible_edges={r:5000+r for r in range(576)},ack_edge=6001,credit_return_delay=7)
def test_two_shard_finite_held_credit_order():
    a=args();a['consumer_edges']=[t for t in a['consumer_edges'] if not 100<=t<300]
    m=D.replay(**a)
    assert m['rows']==576;assert m['peak_reserved_read_seats']==8
    assert [e['row'] for e in m['journal'] if e['kind']=='consumer_accept']==list(range(576))
    assert not m['physical_admission']
    assert set(e['shard'] for e in m['journal'] if e['kind']=='read_accept_reserved')=={0,1}
def test_unknown_consumer_cannot_be_ready():
    a=args();a['consumer_edges']=[]
    with pytest.raises(ValueError):D.replay(**a)
def test_ACK_not_visible():
    a=args();a['visible_edges'][0]=Fraction(1)
    with pytest.raises(ValueError,match='visibility'):D.replay(**a)
def test_early_ACK_rejected():
    a=args();a['ack_edge']=10
    with pytest.raises(ValueError,match='ACK'):D.replay(**a)
def test_no_free_return_or_missing_visibility():
    a=args();a['return_delays'][1]=0
    with pytest.raises(ValueError,match='positive'):D.replay(**a)
    a=args();del a['visible_edges'][575]
    with pytest.raises(ValueError,match='visibility'):D.replay(**a)
def test_phase_is_explicit_and_sameedge_arrival_not_consumed():
    a=args();a['consumer_edges']=range(0,7000,3)
    m=D.replay(**a);assert m['first_consumer_edge']=='12'
    a['consumer_edges']=range(1,7000,3)
    m=D.replay(**a);assert m['first_consumer_edge']=='10'


def test_credit_feedback_not_zero_or_sameedge():
    a=args();a['credit_return_delay']=0
    with pytest.raises(ValueError,match='credit'):D.replay(**a)
    a=args();m=D.replay(**a)
    consumed={e['row']:Fraction(e['time']) for e in m['journal'] if e['kind']=='consumer_accept'}
    retired=[e for e in m['journal'] if e['kind']=='credit_return_capture']
    assert len(retired)==576
    assert all(Fraction(e['time'])==consumed[e['row']]+7 for e in retired)
