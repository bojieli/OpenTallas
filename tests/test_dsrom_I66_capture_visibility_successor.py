import sys,copy,json,importlib.util
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_visibility_successor as S
import dsrom_I66_capture_drain_calendar as OLD
CTX=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=7,user=65536,xversion=52,pc=66)
def owner():
    rows={r:(r%256)//2 for r in range(576)};o=S.Owner(CTX,rows,1)
    for r in range(576):o.capture(r,rows[r],r)
    o.source_terminal(True);return o

def test_source_debt_until_actual_visible_and_captured_return():
    o=owner();assert o.issue(0,CTX,1,0);o.arrive(0,CTX,0,2,0);o.consume(True,3)
    assert not o.issue(1,CTX,4,0)
    with pytest.raises(ValueError):o.captured_credit(0,CTX,5,2)
    o.mark_visible(0,CTX,10)
    with pytest.raises(ValueError):o.captured_credit(0,CTX,11,2)
    assert not o.issue(1,CTX,11,0)
    o.captured_credit(0,CTX,12,2)
    assert not o.issue(1,CTX,12,0)
    assert o.issue(1,CTX,13,0)
    with pytest.raises(ValueError):o.captured_credit(0,CTX,14,2)

def test_visibility_not_delivery_or_alias():
    o=owner();o.issue(0,CTX,1,0);o.arrive(0,CTX,0,2,0)
    with pytest.raises(ValueError):o.mark_visible(0,CTX,3)
    o.consume(True,3)
    with pytest.raises(ValueError):o.mark_visible(0,CTX,3)
    bad=dict(CTX,user=0)
    with pytest.raises(ValueError):o.mark_visible(0,bad,4)

@pytest.mark.parametrize('name',['header_fields','command_fields'])
def test_user32_wire_codec_distinguishes_old16_alias(name):
    w=S.widths();f=w[name];v={k:0 for k in f}
    v['user']=65536;full=S.encode(f,v);assert S.decode(f,full)['user']==65536
    v['user']=0;assert S.encode(f,v)!=full
    v['user']=2**32-1;assert S.decode(f,S.encode(f,v))==v
    v['user']=2**32
    with pytest.raises(ValueError):S.encode(f,v)
    assert w['header_flits']==w['command_flits']==1

def test_old_delivery_credit_is_preserved_negative():
    # Unchanged old schedule; Hubble independent checker correctly rejects it.
    spec=importlib.util.spec_from_file_location('credit_join',S.OUT/'inputs/credit_join.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    a=dict(ctx=CTX,rows={r:(r%256)//2 for r in range(576)},raw={r:r for r in range(576)},capacity=8,
        issue_edges=range(0,6000,3),return_delays={0:9,1:12},consumer_edges=range(2,7000,4),
        visible_edges={r:5000+r for r in range(576)},ack_edge=6001,credit_return_delay=7)
    old=OLD.replay(**a)
    with pytest.raises(ValueError,match='before visibility'):gate.check(old['journal'],7)

def args(c=1):
    return dict(ctx=CTX,capacity=c,issue_edges=range(0,25000,3),return_delays={0:9,1:12},
        consumer_edges=range(2,26000,4),visible_edges={r:40*(r+1) for r in range(576)},ack_edge=26001,credit_return_delay=7)
@pytest.mark.parametrize('c',[1,8])
def test_all576_visibility_anchored_no_reserved_downstream_assumption(c):
    m=S.replay(**args(c))
    spec=importlib.util.spec_from_file_location('credit_join',S.OUT/'inputs/credit_join.py')
    gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
    result=gate.check(m['journal'],7)
    assert result['downstream_transfers']==0
    assert m['peak_source_credit_debt']<=c
    assert not m['separate_downstream_seat_assumed']
    assert not m['actual_provider_qualified']

def test_no_missing_provider_or_zero_credit():
    a=args();a['credit_return_delay']=0
    with pytest.raises(ValueError):S.replay(**a)
    a=args();a['consumer_edges']=[]
    with pytest.raises(ValueError):S.replay(**a)


def test_native_scalar_publication_no_lease_or_missing_writer():
    r=dict(row=0,pos=0,fp32=0x12345678,bf16=0x8000,error=0)
    d=dict(fmt=1,rsplit=576,pw62=0,pw63=0,obase=398720,ops=576)
    w=[dict(family='rom',slot=0,address=398720,data=r['fp32'])]
    m=S.publication_contract(r,d,r['fp32'],w,S.WRITER_FAMILIES)
    assert m['address']==398720
    with pytest.raises(ValueError):S.publication_contract(r,d,r['fp32'],w,S.WRITER_FAMILIES-{'xb'})
    with pytest.raises(ValueError):S.publication_contract(r,d,0,w,S.WRITER_FAMILIES)
    # Equal bits do not grant the competitor ownership or prove safe arbitration.
    w.append(dict(family='xa',slot=0,address=398720,data=r['fp32']))
    with pytest.raises(ValueError):S.publication_contract(r,d,r['fp32'],w,S.WRITER_FAMILIES)
    assert not S.native_source_contract()['existing_ROM_port_not_assumed_free']==False
