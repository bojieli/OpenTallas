from pathlib import Path
import sys
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from qwen_hbm_complete_controller_capture_validated import Capture,FAST,SLOW,pc_of

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

# Archived b0da977ed ACK_entry_fields. These are envelope widths only;
# neither these tests nor the supplied-event model qualify hardware.
IDENTITY_WIDTHS={'instruction':11,'position':21,'die':1,'stack':2,'PC':5,
                 'producer_epoch':64,'transport_epoch':32,'sector':34,'tag':16}
CALLBACKS=('lock_partial','read_import_retired','merge_result','column',
           'backing_visible','capture','ACK_consumer_retire','reverse_credit')

def callback_fixture(callback):
    c=Capture();q=owner();mask=1
    if callback=='lock_partial':return c,q,[mask]
    c.lock_partial(q,mask)
    if callback=='read_import_retired':return c,q,[0]
    c.read_import_retired(q,0)
    if callback=='merge_result':return c,q,[('XOR','AND','XOR'),0,27*SLOW]
    c.merge_result(q,('XOR','AND','XOR'),0,27*SLOW)
    t=c.edge(27*SLOW+FAST)
    if callback=='column':return c,q,[t,mask,'fixture',1000000]
    assert c.column(q,t,mask,'fixture',1000000)
    v=c.edge(t+7274)
    if callback=='backing_visible':return c,q,[v]
    c.backing_visible(q,v);capture=c.edge(v+10000)
    if callback=='capture':return c,q,[capture]
    assert c.capture(q,capture);retire=100000*SLOW
    if callback=='ACK_consumer_retire':return c,q,[retire]
    c.ACK_consumer_retire(q,retire)
    return c,q,[c.edge(retire)+3*FAST]

def reject_without_mutation(c,callback,q,args):
    from copy import deepcopy
    before=deepcopy(vars(c));envelope=deepcopy(q);arguments=deepcopy(args)
    with pytest.raises(ValueError):getattr(c,callback)(q,*args)
    assert vars(c)==before
    assert q==envelope and args==arguments

@pytest.mark.parametrize('callback',CALLBACKS)
@pytest.mark.parametrize('field,value',[
    (field,value) for field,bits in IDENTITY_WIDTHS.items()
    for value in (-1,1<<bits,False,True,0.0,'0',None)
])
def test_invalid_identity_rejected_before_any_callback_mutation(callback,field,value):
    c,q,args=callback_fixture(callback)
    reject_without_mutation(c,callback,dict(q,**{field:value}),args)

@pytest.mark.parametrize('callback',CALLBACKS)
@pytest.mark.parametrize('malformation',('missing','extra','not_mapping'))
def test_incomplete_identity_rejected_before_mutation(callback,malformation):
    c,q,args=callback_fixture(callback)
    if malformation=='missing':del q['instruction']
    elif malformation=='extra':q['unbound_payload']=0
    else:q=None
    reject_without_mutation(c,callback,q,args)

@pytest.mark.parametrize('callback',CALLBACKS)
def test_valid_width_wrong_physical_PC_rejected_before_mutation(callback):
    c,q,args=callback_fixture(callback)
    reject_without_mutation(c,callback,dict(q,PC=q['PC']^1),args)

@pytest.mark.parametrize('callback',('lock_partial','column'))
@pytest.mark.parametrize('mask',(-1,0,1<<32,False,True,1.0,float(0xffffffff),'1',None))
def test_malformed_masks_rejected_before_mutation(callback,mask):
    c,q,args=callback_fixture(callback)
    args[0 if callback=='lock_partial' else 1]=mask
    reject_without_mutation(c,callback,q,args)

def test_float_fullwrite_mask_cannot_enter_pending():
    c=Capture();q=owner()
    reject_without_mutation(c,'column',q,[0,float(0xffffffff),'fixture',1000000])

def test_fullwrite_mask_cannot_acquire_partial_lock():
    reject_without_mutation(Capture(),'lock_partial',owner(),[0xffffffff])

TIME_ARGUMENTS=[('read_import_retired',0),('merge_result',1),('merge_result',2),
                ('column',0),('column',3),('backing_visible',0),('capture',0),
                ('ACK_consumer_retire',0),('reverse_credit',0)]

@pytest.mark.parametrize('callback,index',TIME_ARGUMENTS)
@pytest.mark.parametrize('time',(-1,False,True,float('nan'),float('inf'),float('-inf'),
                                 None,'not-a-time','1/0',[],{}))
def test_malformed_timestamps_rejected_before_mutation(callback,index,time):
    c,q,args=callback_fixture(callback);args[index]=time
    reject_without_mutation(c,callback,q,args)

@pytest.mark.parametrize('field,bits',IDENTITY_WIDTHS.items())
def test_identity_unsigned_boundaries_are_preserved(field,bits):
    for value in (0,(1<<bits)-1):
        q=owner();q[field]=value
        if field=='sector':q['PC']=pc_of(value)
        elif field=='PC':q=owner(pc=value)
        identity=Capture.identity(q)
        assert dict(zip(sorted(q),identity))==q

def test_valid_fraction_timestamps_keep_simulation_precision_and_no_hardware_width():
    from fractions import Fraction
    for value,expected in [(0,0),(0.5,Fraction(1,2)),('1/3',Fraction(1,3)),
                           (27*SLOW,27*SLOW),(1<<80,1<<80)]:
        assert Capture.time(value)==expected
    c,q,args=callback_fixture('reverse_credit')
    assert c.reverse_credit(q,*args) is None
    assert c.quiescent()

# Callback-owner regressions use valid typed ledger transactions and existing
# timing formulas. No arithmetic/payload execution or hardware qualification.
def advance_write(c,q,start=0,mask=0xffffffff,through='RETIRED'):
    from math import ceil
    assert c.column(q,start,mask,'fixture',1000000)
    if through=='COLUMN':return
    visible=c.edge(start+7274);c.backing_visible(q,visible)
    if through=='VISIBLE':return
    captured=c.edge(visible+10000);assert c.capture(q,captured)
    if through=='CAPTURED':return
    retired=(ceil((captured+FAST)/SLOW)+3)*SLOW
    c.ACK_consumer_retire(q,retired)
    return c.edge(retired)+3*FAST

@pytest.mark.parametrize('state',('COLUMN','VISIBLE','CAPTURED','RETIRED'))
def test_pending_fullwrite_prevents_new_same_address_partial_lock_before_mutation(state):
    c=Capture();a=owner(epoch=1);b=dict(a,tag=1,instruction=11)
    credit=advance_write(c,a,through=state)
    assert c.pending[c.identity(a)]['state']==state
    reject_without_mutation(c,'lock_partial',b,[1])
    assert not c.locks and not c.quiescent()
    # Address exclusion does not become channel-wide serialization.
    other=dict(b,sector=a['sector']+1);other['PC']=pc_of(other['sector'])
    c.lock_partial(other,1)
    assert c.locks[c.address(other)]['identity']==c.identity(other)
    if state=='RETIRED':
        c.reverse_credit(a,credit)
        assert c.locks[c.address(other)]['identity']==c.identity(other)
        assert not c.quiescent()

@pytest.mark.parametrize('mask',(1,0xffffffff))
def test_spent_identity_cannot_reacquire_partial_lock_after_reverse_credit(mask):
    c=Capture();q=owner(epoch=1);start=0
    if mask==1:
        c.lock_partial(q,mask);c.read_import_retired(q,0)
        c.merge_result(q,('XOR','AND','XOR'),0,27*SLOW)
        start=c.edge(27*SLOW+FAST)
    credit=advance_write(c,q,start,mask);c.reverse_credit(q,credit)
    assert c.quiescent() and c.identity(q) in c.seen
    reject_without_mutation(c,'lock_partial',q,[1])
    assert c.quiescent()

def test_fresh_same_address_partial_owner_completes_only_after_old_reverse_credit():
    c=Capture();a=owner(epoch=1);b=dict(a,tag=1,instruction=11)
    credit=advance_write(c,a)
    reject_without_mutation(c,'lock_partial',b,[1])
    c.reverse_credit(a,credit);assert c.quiescent()
    c.lock_partial(b,1);c.read_import_retired(b,credit)
    c.merge_result(b,('XOR','AND','XOR'),credit,credit+27*SLOW)
    start=c.edge(credit+27*SLOW+FAST)
    next_credit=advance_write(c,b,start,1)
    assert c.locks[c.address(b)]['identity']==c.identity(b)
    assert not c.quiescent()
    third=dict(a,tag=2,instruction=12)
    reject_without_mutation(c,'column',third,[next_credit,0xffffffff,'fixture',1000000])
    c.reverse_credit(b,next_credit);assert c.quiescent()
    final_credit=advance_write(c,third,next_credit)
    c.reverse_credit(third,final_credit);assert c.quiescent()

def test_reverse_credit_rejects_foreign_lock_in_legacy_ledger_before_any_deletion():
    from copy import deepcopy
    c=Capture();a=owner(epoch=1);b=dict(a,tag=1,instruction=11)
    credit=advance_write(c,a)
    # Restore the legacy overlap asserted by repro_owner_release.py: a retired
    # full WR and a newer partial lock whose read-import callback has retired.
    # Corrected lock acquisition prevents this state; reverse release must also
    # reject it defensively rather than delete the foreign owner or old pending.
    retired=c.pending[c.identity(a)]['retired']
    legacy=Capture();legacy.lock_partial(b,1);legacy.read_import_retired(b,retired)
    c.locks=deepcopy(legacy.locks)
    reject_without_mutation(c,'reverse_credit',a,[credit])
    assert c.pending[c.identity(a)]['state']=='RETIRED'
    assert c.locks[c.address(b)]['identity']==c.identity(b)
    assert not c.quiescent()
    c.merge_result(b,('XOR','AND','XOR'),retired,retired+27*SLOW)
    assert c.locks[c.address(b)]['merged']==retired+27*SLOW
