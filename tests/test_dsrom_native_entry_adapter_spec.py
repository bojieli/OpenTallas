import importlib.util
import json
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('entry_spec',ROOT/'tools/dsrom_native_entry_adapter_spec.py')
M=importlib.util.module_from_spec(spec);spec.loader.exec_module(M)


def test_all_bf16_encodings_are_idempotent():
    assert all(M.bf16_reround_bits(b<<16)==b<<16 for b in range(65536))


def test_source_specific_versions_and_head_separation():
    d=M.build();c={r['consumer']:r for r in d['producer_certificates']}
    assert len(c)==7
    assert c['L2.I24']['producer']==c['L2.I25']['producer']=='L2.I6'
    assert c['L8.I24']['producer']==c['L8.I25']['producer']=='L8.I6'
    assert c['L14.I34']['producer']==c['L14.I35']['producer']=='L14.I16'
    assert c['Lhead.I5']['producer']=='Lhead.I4'
    assert c['Lhead.I5']['dedicated_head_unbound']
    assert not d['reduction_order_and_full_bitexactness_admission']


@pytest.mark.parametrize('field,value',[('rnd',0),('pred',1),('o_si',2),('su_nin',1280)])
def test_producer_mutation_refuses_certificate(field,value):
    row=json.loads((M.OUT/'inputs/phase_producers.json').read_text())['proofs'][0]
    row['producer']['instruction'][field]=value
    with pytest.raises(ValueError):M.input_certificate(row)


@pytest.mark.parametrize('eid',[384,0xffffffff,0x80000000,-1])
def test_full32_EID_rejected_before_arithmetic(eid):
    with pytest.raises(ValueError):M.checked_key(eid,0,4096)


def test_wide_key_no_truncation():
    assert M.checked_key(383,0,4096)==383*4096
    with pytest.raises(ValueError):M.checked_key(383,(1<<30)-1,4096)


def test_one_actual_accepted_read_and_registered_GO():
    e=M.EntryLease(('rank0','lease7','gen1'),True)
    e.vm_request(False);assert e.vm_reads==0
    e.vm_request(True)
    with pytest.raises(ValueError):e.vm_request(True)
    assert e.vm_response(e.owner,383)==383*4096
    assert e.lookup(True,True,True)
    e.fence(31,32);e.arm(32,True)
    with pytest.raises(ValueError):e.commit(32,e.owner,True)
    with pytest.raises(ValueError):e.commit(33,e.owner,False)
    e.commit(33,e.owner,True);assert e.accepted_go==1
    with pytest.raises(ValueError):e.commit(34,e.owner,True)
    with pytest.raises(ValueError):e.drain(True,False)
    e.drain(True,True);assert e.state=='RELEASED'


def test_bad_EID_no_LOOK_GO_after_accepted_read():
    e=M.EntryLease('owner',True);e.vm_request(True)
    with pytest.raises(ValueError):e.vm_response('owner',0xffffffff)
    assert e.state=='CANCEL' and e.accepted_go==0 and e.vm_reads==1
    with pytest.raises(ValueError):e.lookup(True,True,True)


@pytest.mark.parametrize('hit,predicate,phase',[(False,True,True),(True,False,True),(True,True,False)])
def test_fault_suppresses_LOOK_to_GO(hit,predicate,phase):
    e=M.EntryLease('owner',False)
    assert not e.lookup(hit,phase,predicate)
    with pytest.raises(ValueError):e.arm(100,True)
    assert e.accepted_go==0


def test_cancel_quarantines_one_read_no_reread_or_CAM():
    e=M.EntryLease('owner',True);e.vm_request(True);e.cancel()
    with pytest.raises(ValueError):e.drain(True,False)
    with pytest.raises(ValueError):e.vm_response('stale-generation',1)
    assert e.vm_response('owner',1) is None
    with pytest.raises(ValueError):e.lookup(True,True,True)
    e.drain(True,False);assert e.vm_reads==1 and e.accepted_go==0


def test_cancel_before_and_after_registered_accept():
    e=M.EntryLease('owner',False);e.lookup(True,True,True);e.fence(10,11);e.arm(11,True);e.cancel()
    with pytest.raises(ValueError):e.commit(12,'owner',True)
    assert e.accepted_go==0
    e=M.EntryLease('owner',False);e.lookup(True,True,True);e.fence(10,11);e.arm(11,True);e.commit(12,'owner',True);e.cancel()
    assert e.accepted_go==1 and e.state=='WAIT'
    with pytest.raises(ValueError):e.drain(True,False)
    e.drain(True,True)


def receipts():
    return [dict(owner='owner',phase=6,pair=pair,word_index=w,logical_address=150+w,
        command_edge=w+1,capture_edge=w+2,ECC_terminal_edge=w+3,delivery_edge=w+4,
        capture_accepted=True,ECC_good_or_corrected=True,uncorrectable=False,
        consumer_delivery_accepted=True) for pair in range(2) for w in range(25)]


def test_cfg_fence_is_all_delivered_words_not_timer():
    assert M.cfg_delivery_fence(receipts(),'owner',6,{0,1})==28
    with pytest.raises(ValueError):M.cfg_delivery_fence(receipts()[:-1],'owner',6,{0,1})
    with pytest.raises(ValueError):M.cfg_delivery_fence(receipts()+[receipts()[0]],'owner',6,{0,1})


@pytest.mark.parametrize('field,value',[('owner','oldgen'),('ECC_good_or_corrected',False),
    ('uncorrectable',True),('consumer_delivery_accepted',False),('capture_accepted',False),
    ('logical_address',0),('capture_edge',1)])
def test_cfg_poison_and_stale_cannot_fence(field,value):
    r=receipts();r[0][field]=value
    with pytest.raises(ValueError):M.cfg_delivery_fence(r,'owner',6,{0,1})


def test_replay_default_off_no_zero_cost_qualification():
    d=M.build()
    assert d['default'] is False and d['area_and_finite_timing_unpriced_not_zero']
    assert not d['full_token_or_physical_admission']
    assert d['cfg_calendar']['accepted_per_phase_word_deliveries']==102400
    assert (M.OUT/'model-r1.json').read_text()==json.dumps(d,indent=2,sort_keys=True)+'\n'
