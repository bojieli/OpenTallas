import copy
import sys
from pathlib import Path
import pytest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from w17_D1_event_ledger import Ledger, admission

def event(kind='WRITE_ACCEPT', **kw):
    e=dict(kind=kind,owner=0,generation=1,operation=4,address=264303,tag=0,beat=0,state=1)
    e.update(kw); return e

def rejected_without_mutation(ledger, **kw):
    before=copy.deepcopy(ledger)
    with pytest.raises(ValueError): ledger.step(**kw)
    assert ledger==before

def test_realistic_32_intent_single_credit_ledger():
    l=Ledger()
    for i in range(32):
        e=event(operation=i,address=264303+(i//2 if i%2==0 else 16),tag=i//2 if i%2==0 else 16,state=1 if i%2==0 else 3)
        l.step(cycle=317+i*25,fault=False,event=e)
        l.step(cycle=330+i*25,fault=False,event=dict(e,kind='WRITE_ACK',state=2 if i%2==0 else 4))
    assert (l.accepted,l.retired,l.pending)==(32,32,None)

def test_read_return_owned_and_generation_qualified():
    l=Ledger(); l.step(cycle=1,fault=False,event=event('READ_ACCEPT',state=5))
    l.step(cycle=35,fault=False,event=event('READ_RETURN',state=6))
    assert l.retired==1

@pytest.mark.parametrize('bad',[dict(owner=1),dict(generation=2),dict(operation=3),dict(address=264319),dict(tag=16),dict(beat=1),dict(state=1)])
def test_wrong_callback_rejected_before_mutation(bad):
    l=Ledger(); l.step(cycle=1,fault=False,event=event())
    rejected_without_mutation(l,cycle=2,fault=False,event=event('WRITE_ACK',state=2,**bad) if 'state' not in bad else event('WRITE_ACK',**bad))

@pytest.mark.parametrize('bad',[True,1.5,-1,1<<64,'1'])
def test_bad_cycle(bad): rejected_without_mutation(Ledger(),cycle=bad,fault=False,event=event())

def test_fault_and_ack_same_edge_and_late_ack():
    l=Ledger(); l.step(cycle=1,fault=False,event=event())
    rejected_without_mutation(l,cycle=2,fault=True,event=event('WRITE_ACK',state=2))
    l.step(cycle=2,fault=True)
    rejected_without_mutation(l,cycle=3,fault=False,event=event('WRITE_ACK',state=2))

def test_early_duplicate_unaccepted_spent_and_pending():
    l=Ledger(); rejected_without_mutation(l,cycle=1,fault=False,event=event('WRITE_ACK',state=2))
    l.step(cycle=1,fault=False,event=event())
    rejected_without_mutation(l,cycle=1,fault=False,event=event('WRITE_ACK',state=2))
    rejected_without_mutation(l,cycle=2,fault=False,event=event(operation=5))
    l.step(cycle=2,fault=False,event=event('WRITE_ACK',state=2))
    rejected_without_mutation(l,cycle=3,fault=False,event=event('WRITE_ACK',state=2))
    rejected_without_mutation(l,cycle=3,fault=False,event=event())

@pytest.mark.parametrize('kind',['BUSY','PC','PREDICTED_COMPLETION','STATIC_READY'])
def test_noncausal_progress(kind): rejected_without_mutation(Ledger(),cycle=1,fault=False,event=event(kind))

def test_admission_four_predicates_truth_table():
    for mask in range(16):
        bits=[bool(mask>>i&1) for i in range(4)]
        p=dict(zip(['me_ready','kv_ok','kvd_v','win_idle'],bits),available=True)
        assert admission(p)==(mask==11)
    assert admission(dict(available=False,me_ready=None,kv_ok=None,kvd_v=None,win_idle=None)) is None
    with pytest.raises(ValueError): admission(dict(available=False,me_ready=False,kv_ok=False,kvd_v=False,win_idle=False))
