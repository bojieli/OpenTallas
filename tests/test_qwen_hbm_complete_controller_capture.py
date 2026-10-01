from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_controller_capture import Capture,FAST,SLOW,pc_of

def owner(pc=0,tag=0,epoch=(1<<64)-1):
    sector=next(s for s in range(4096) if pc_of(s)==pc)
    return dict(die=0,stack=0,PC=pc,sector=sector,tag=tag,producer_epoch=epoch,transport_epoch=7,instruction=10,position=0)

def test_32_PC_wave_and_held_ACK_preserve_full_epoch_and_finite_capacity():
    c=Capture();qs=[owner(pc,pc) for pc in range(32)]
    for q in qs:assert c.column(q,0,0xffffffff,'fixture-rowhit',1000000)
    assert len(c.pending)==32
    for q in qs:c.backing_visible(q,9*FAST)
    ready=c.edge(9*FAST+10000)
    for q in qs[:4]:assert c.capture(q,ready)
    assert not c.capture(qs[4],ready)
    assert len(c.ACK[0,0])==4 and len(c.pending)==32
    for field in ('producer_epoch','transport_epoch','tag'):
        bad=dict(qs[0]);bad[field]=bad[field]^1
        with pytest.raises(KeyError):c.backing_visible(bad,ready)
    with pytest.raises(ValueError,match='head'):c.ACK_consumer_retire(qs[1],100000)
    assert not c.quiescent()

def test_partial_read_merge_WR_visible_ACK_retire_credit_no_early_release():
    c=Capture();q=owner();mask=1
    with pytest.raises(ValueError,match='partial'):c.column(q,0,mask,'fixture',1000000)
    c.lock_partial(q,mask);c.read_import_retired(q,0)
    with pytest.raises(ValueError,match='merge latency'):c.merge_result(q,('XOR','AND','XOR'),0,1)
    c.merge_result(q,('XOR','AND','XOR'),0,27*SLOW)
    t=c.edge(27*SLOW+FAST);assert c.column(q,t,mask,'fixture',1000000)
    with pytest.raises(ValueError,match='backing'):c.backing_visible(q,t)
    with pytest.raises(ValueError,match='reverse'):c.reverse_credit(q,t)
    v=c.edge(t+7274);c.backing_visible(q,v);assert c.capture(q,c.edge(v+10000))
    r=100000*SLOW;c.ACK_consumer_retire(q,r)
    assert c.locks and c.pending
    c.reverse_credit(q,c.edge(r)+3*FAST);assert c.quiescent()

def test_depth_one_stalls_same_PC_without_stack_global_serialization():
    c=Capture(depth=1);q=owner();assert c.column(q,0,0xffffffff,'fixture',1000000)
    nextq=dict(q,tag=1,sector=q['sector']+4096)
    # Select a distinct address on the same actual PC.
    nextq['sector']=next(s for s in range(4096,10000) if pc_of(s)==q['PC'])
    assert not c.column(nextq,2*FAST,0xffffffff,'fixture',1000000)
    assert c.column(owner(1,2),0,0xffffffff,'fixture',1000000)
    with pytest.raises(ValueError,match='binding'):c.column(owner(2,3),0,0xffffffff,None,None)

def test_five_per_PC_slots_stall_sixth_and_late_capture_delays_consumer():
    c=Capture();sectors=[s for s in range(8192) if pc_of(s)==0][:6]
    qs=[dict(owner(),sector=s,tag=i) for i,s in enumerate(sectors)]
    for i,q in enumerate(qs[:5]):assert c.column(q,2*i*FAST,0xffffffff,'fixture',1000000)
    assert not c.column(qs[5],10*FAST,0xffffffff,'fixture',1000000)
    q=qs[0];c.backing_visible(q,9*FAST)
    late=100000*FAST;assert c.capture(q,late)
    with pytest.raises(ValueError,match='CDC'):c.ACK_consumer_retire(q,100*SLOW)
