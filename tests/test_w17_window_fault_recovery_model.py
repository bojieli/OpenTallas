import importlib.util
from pathlib import Path
import sys
import pytest
P=Path(__file__).resolve().parents[1]/'tools/w17_window_fault_recovery_model.py'
spec=importlib.util.spec_from_file_location('recovery',P);m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
def id_at(model,sector=0):return model.reserve(sector,262144+sector)
def drain(model,identity):model.complete(identity);model.offer(identity);model.consume(identity)

def test_fault_preserves_accepted_and_cancel_only_unaccepted():
 r=m.RecoveryModel();a=id_at(r);b=id_at(r,1);r.accept(a);r.fault(4)
 with pytest.raises(m.Rejected):r.cancel(a)
 r.cancel(b)
 with pytest.raises(m.Rejected):r.reserve(2,262146)
 with pytest.raises(m.Rejected):r.reset()
 assert r.state()['outstanding']==1 and r.fault_code==4
 drain(r,a);assert r.retired==1 and r.fault_code==4
 with pytest.raises(m.Rejected):r.restart()
 m.model_only_fence(r);assert r.can_restart() and not r.rtl_admission();r.restart();assert r.lease==1 and not r.fault_code

def test_held_response_and_sync_async_reset_are_not_retirement():
 r=m.RecoveryModel();a=id_at(r);r.accept(a);r.complete(a);r.offer(a);r.fault(16)
 for _ in range(100):assert not r.consume(a,False)
 assert r.accepted==1 and r.retired==0 and len(r.entries)==1
 with pytest.raises(m.Rejected):r.reset()
 with pytest.raises(m.Rejected):m.model_only_fence(r)
 r.consume(a);m.model_only_fence(r);r.reset();assert r.epoch==0 and r.lease==1

def test_delayed_stale_duplicate_after_fault_does_not_free_new_owner():
 r=m.RecoveryModel();old=id_at(r);r.accept(old);r.fault(4);drain(r,old);m.model_only_fence(r);r.restart()
 new=id_at(r);r.accept(new);before=r.state()
 with pytest.raises(m.Rejected):r.inject(old)
 assert r.accepted==before['accepted'] and r.retired==before['retired'] and new in r.entries
 assert r.fault_code==4 and not r.can_restart()
 drain(r,new)
 with pytest.raises(m.Rejected):r.inject(new)
 assert r.retired==2

def test_512_wrap_ghost_is_indistinguishable_on_actual_wire_but_not_lease():
 r=m.RecoveryModel();old=id_at(r);r.accept(old);drain(r,old)
 for _ in range(512):r.fault(4);m.model_only_fence(r);r.restart()
 new=id_at(r);r.accept(new);r.complete(new);r.offer(new)
 assert old.wire_tag==new.wire_tag and old.address==new.address and old.lease!=new.lease
 assert m.candidate_wire_accepts(r.epoch,{0},set(),old.wire_tag)
 with pytest.raises(m.Rejected):r.inject(old)
 assert new in r.entries and r.retired==1
 assert not r.rtl_admission() # full identities/fence are missing in actual interface

def test_per_pc_return_head_and_lowest_pc_selection():
 r=m.RecoveryModel();a=id_at(r,0);b=id_at(r,4);c=id_at(r,1)
 for i in (a,b,c):r.accept(i);r.complete(i)
 with pytest.raises(m.Rejected):r.offer(c)
 r.offer(a);r.offer(b)
 with pytest.raises(m.Rejected):r.consume(b)
 r.consume(a);r.offer(c);r.consume(c);r.consume(b);assert r.retired==3

def test_karb_held_request_remains_owned_after_fault():
 r=m.RecoveryModel();a=id_at(r);r.accept(a,pipe_out=True);r.fault(4)
 with pytest.raises(m.Rejected):r.cancel(a)
 with pytest.raises(m.Rejected):r.restart()
 r.backend_accept(a);drain(r,a);m.model_only_fence(r);r.restart()

@pytest.mark.parametrize('actor',m.ACTORS)
def test_missing_each_end_to_end_ack_blocks_restart(actor):
 r=m.RecoveryModel();r.fault(4);m.model_only_fence(r);del r.acks[actor]
 with pytest.raises(m.Rejected):r.restart()

@pytest.mark.parametrize('field,value',[('lease',1),('revision',100),('outstanding',1),('frozen',False),('no_future_delivery',False),('q',(1,)+(0,)*31),('r',(1,)+(0,)*31),('held',(1,)+(0,)*31)])
def test_bad_or_nonempty_ack_rejected(field,value):
 r=m.RecoveryModel();r.fault(4);values=dict(actor='DELIVERY_FENCE',lease=0,revision=r.revision,outstanding=0,no_future_delivery=True);values[field]=value
 with pytest.raises(m.Rejected):r.acknowledge(m.DrainAck(**values))

def test_invalid_arrival_invalidates_already_collected_ack():
 r=m.RecoveryModel();a=id_at(r);r.cancel(a);r.fault(4);m.model_only_fence(r)
 with pytest.raises(m.Rejected):r.inject(a)
 assert not r.can_restart() and not r.acks

@pytest.mark.parametrize('field,value',[('lease',-1),('serial',2**64),('epoch',512),('sector',17),('beat',1),('owner','CKV'),('pc',31),('address',2**30),('epoch',True)])
def test_typed_identity_apertures(field,value):
 v=dict(lease=0,serial=0,epoch=0,sector=0,pc=0,address=262144);v[field]=value
 with pytest.raises(m.Rejected):m.Identity(**v)

def test_capacity_and_counter_exhaustion_fail_closed():
 r=m.RecoveryModel();ids=[id_at(r,n) for n in range(8)]
 with pytest.raises(m.Rejected):id_at(r,8)
 for i in ids:r.cancel(i)
 r.serial=2**64-1
 with pytest.raises(m.Rejected):id_at(r)
 r.fault(4);m.model_only_fence(r);r.lease=2**64-1
 # Reissue matching fence for terminal generation, then fail without wrap.
 r.acks.clear();m.model_only_fence(r)
 with pytest.raises(m.Rejected):r.restart()

def test_adversarial_eight_credit_fault_drain_and_false_fence():
 r=m.RecoveryModel();ids=[id_at(r,n) for n in range(8)]
 for i in ids:r.accept(i)
 r.fault(4)
 for i in reversed(ids):r.complete(i)
 while r.entries:
  for pc in range(32):
   if r.return_order[pc]:
    head=r.return_order[pc][0]
    if r.entries[head]==m.Phase.RETURN:r.offer(head)
  i=min((i for i,p in r.entries.items() if p==m.Phase.HELD),key=lambda i:i.pc)
  assert not r.consume(i,False)
  with pytest.raises(m.Rejected):m.model_only_fence(r)
  r.consume(i)
 m.model_only_fence(r);r.restart();assert r.retired==8
