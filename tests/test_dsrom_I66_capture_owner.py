import sys,copy
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_I66_capture_owner as O
CTX=dict(stage=0,rank=0,expert=0,phase=10,key_word=2149580800,generation=7,user=3,xversion=52,pc=66)
def make(c=2):
    rows={r:(r%256)//2 for r in range(576)};o=O.Owner(CTX,rows,c)
    for r in range(576):o.capture(r,rows[r],r)
    o.source_terminal(True);return o
@pytest.mark.parametrize('name',[n for n,w in O.CONTEXT])
def test_stale_fields(name):
    o=make();ctx=copy.deepcopy(CTX);ctx[name]^=1
    with pytest.raises(ValueError):o.issue(0,ctx,1,0)
def test_held_outoforder_nooverflow():
    o=make();assert o.issue(0,CTX,1,0);assert o.issue(1,CTX,2,0);assert not o.issue(2,CTX,3,0)
    o.arrive(1,CTX,1,4,0);assert o.consume(True,5) is None
    o.arrive(0,CTX,0,5,0);assert o.consume(False,6) is None
    assert o.consume(True,6)==(0,0);assert o.issue(2,CTX,6,0)
    assert o.consume(True,7)==(1,1)
    with pytest.raises(ValueError):o.arrive(1,CTX,1,7,0)
def test_allrows_and_causal_visibility():
    o=make(1)
    for row in range(576):
        assert o.issue(row,CTX,3*row+1,(row%256)//128);o.arrive(row,CTX,row,3*row+2,(row%256)//128)
        assert o.consume(True,3*row+3)==(row,row)
    with pytest.raises(ValueError):o.release(True,True,True)
    for row in range(576):o.mark_visible(row,CTX)
    with pytest.raises(ValueError):o.release(True,False,True)
    o.packet_ack(CTX,1729,True,True)
    o.release(True,True,True)
def test_geometry_no_default_zero():
    with pytest.raises(ValueError):O.geometry_gate({})
def test_no_clock_or_pipeline_selection():
    m=O.model();assert m['native_clock'].startswith('one source clk')
    assert m['added_pipeline_state_bits'] is None
    assert m['consumer_first_edge'] is None
    assert not m['positions_selected']
    assert not m['RTL_or_build_admitted']
    assert m['proposed_request_bits']==187;assert m['proposed_return_bits']==240
def test_hold_repair_pairing():
    h=O.hold_repair()
    assert h['total_feedback_BUF']==2*(39744+1483)
    for v in h['typed_paths'].values():
        assert v['required_allowed_BUF_lower_bound']==2
        assert v['conditional_margin_ps']>0
        assert not v['actual_geometry_qualified']

def test_physical_shard_cannot_alias():
    o=make()
    with pytest.raises(ValueError):o.issue(0,CTX,1,1)
    assert o.issue(0,CTX,1,0)
    with pytest.raises(ValueError):o.arrive(0,CTX,0,2,1)

def test_scalar_read_one_per_edge():
    o=make();assert o.issue(0,CTX,1,0)
    with pytest.raises(ValueError):o.issue(1,CTX,1,0)

@pytest.mark.parametrize('fmt,pw62,pw63,row,expected',[(1,0,0,0,0x12345678),(2,1,1,0,0x80000000),(0,1,0,0,0x12345678),(0,1,0,1,0x80000000)])
def test_source_formatter_keeps_supplied_bits(fmt,pw62,pw63,row,expected):
    r=dict(row=row,pos=0,fp32=0x12345678,bf16=0x8000,error=0)
    d=dict(fmt=fmt,rsplit=1,pw62=pw62,pw63=pw63,obase=398720,ops=576)
    assert O.source_formatter(r,d)==(398720+row,expected)
@pytest.mark.parametrize('cause',['alias','error'])
def test_formatter_no_silent_alias_or_error(cause):
    r=dict(row=0,pos=0,fp32=0,bf16=0,error=int(cause=='error'))
    d=dict(fmt=1,rsplit=1,pw62=0,pw63=0,obase=(1<<19) if cause=='alias' else 398720,ops=576)
    with pytest.raises(ValueError):O.source_formatter(r,d)


def test_same_edge_return_is_not_acceptance():
    o=make();o.issue(0,CTX,1,0);o.arrive(0,CTX,0,2,0)
    with pytest.raises(ValueError):o.consume(True,2)
    assert o.consume(True,3)==(0,0)

def test_delivery_ack_cannot_replace_home_visibility():
    o=make(1)
    with pytest.raises(ValueError):o.packet_ack(CTX,1,True,True)
    for r in range(576):
        o.issue(r,CTX,3*r+1,(r%256)//128);o.arrive(r,CTX,r,3*r+2,(r%256)//128);o.consume(True,3*r+3)
    with pytest.raises(ValueError):o.packet_ack(CTX,1728,True,True)
    with pytest.raises(ValueError):o.packet_ack(CTX,1729,False,True)
    o.packet_ack(CTX,1729,True,True)
    with pytest.raises(ValueError):o.release(True,True,True)
    with pytest.raises(ValueError):o.packet_ack(CTX,1730,True,True)


def test_forward_hold_not_paid_by_feedback():
    m=O.forward_hold_obligations()
    x=next(p for p in m['paths'] if p['launch']==O.T.C.HQ and p['destination']==O.T.C.HQ and p['series_NAND']==0)
    assert x['required_BUF_minimum']==3
    assert O.hold_repair()['typed_paths'][O.T.C.HQ]['required_allowed_BUF_lower_bound']==2
    assert m['total_added_forward_BUF_cells'] is None
    assert all(not p['actual_routes_load_slew_and_clock_correlation_qualified'] for p in m['paths'])


def test_complete_context_missing_key_and_PC_charged():
    p=O.model()['state_price_equations']
    assert p['frozen_context_existing_baseline_bits']+p['required_extra_frozen_identity_bits']==169
    assert p['extra_frozen_identity_hold_BUF_lower_bound']==92
    assert p['context_replication_to_remote_shard_additional_bits'] is None
