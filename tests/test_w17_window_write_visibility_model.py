import importlib.util
from pathlib import Path
import sys
import pytest
P=Path(__file__).resolve().parents[1]/'tools/w17_window_write_visibility_model.py'
s=importlib.util.spec_from_file_location('write_visibility',P);m=importlib.util.module_from_spec(s);sys.modules[s.name]=m;s.loader.exec_module(m)
def identity(serial=0,address=262144,mask=0xffffffff):return m.WriteIdentity(0,serial,address,mask)

def test_all1000_column_phases_seven_sufficient_six_fails():
 witnesses=[]
 for phase in range(1000):
  t=m.timing(phase)
  assert t['guarded_ps']>=t['physical_visible_ps']
  if t['source_ack_ps']+6000<t['physical_visible_ps']:witnesses.append(phase)
 assert 0 in witnesses and len(witnesses)==274

def test_fault_ack_pendingzero_not_physical_drain():
 r=m.WriteVisibilityLedger();i=identity();r.accept(i);r.issue(i,0);r.acknowledge(i,1000);r.fault(4)
 assert r.state()['logically_empty'] and r.state()['owned']==1 and not r.reset_allowed()
 with pytest.raises(m.Rejected):r.retire_visible(i,7000)
 r.retire_visible(i,8000);assert r.reset_allowed() and not r.rtl_admission()

def test_last32nd_ack_guard_covers_prior_code_and_masked_scale_writes():
 r=m.WriteVisibilityLedger();ids=[];last_ack=0
 for n in range(32):
  i=identity(n,262144+n//2 if n%2==0 else 262160,0xffffffff if n%2==0 else 1<<(n//2))
  column=n*3000+999;r.accept(i);r.issue(i,column);last_ack=m.timing(column)['source_ack_ps'];r.acknowledge(i,last_ack);ids.append(i)
 assert len(r.owned)==32 and r.transport_acked==32
 for i in ids:r.retire_visible(i,last_ack+7000)
 assert r.visible_retired==32 and not r.owned

@pytest.mark.parametrize('action',['issue','ack','retire'])
def test_stale_write_identity_never_releases_owned(action):
 r=m.WriteVisibilityLedger();i=identity();wrong=identity(1);r.accept(i);r.issue(i,0);r.acknowledge(i,1000)
 with pytest.raises(m.Rejected):
  if action=='issue':r.issue(wrong,0)
  elif action=='ack':r.acknowledge(wrong,1000)
  else:r.retire_visible(wrong,8000)
 assert i in r.owned

def test_duplicate_ack_and_early_ack_rejected():
 r=m.WriteVisibilityLedger();i=identity();r.accept(i);r.issue(i,999)
 with pytest.raises(m.Rejected):r.acknowledge(i,1000)
 r.acknowledge(i,2000)
 with pytest.raises(m.Rejected):r.acknowledge(i,2000)
 assert r.transport_acked==1 and len(r.owned)==1

def test_user1_outside_baseline_allocation_and_clock_change_fail_closed():
 r=m.WriteVisibilityLedger()
 with pytest.raises(m.Rejected):r.accept(identity(address=264320))
 with pytest.raises(m.Rejected):m.WriteVisibilityLedger(clk_ps=833)

def test_fault_before_issue_preserves_queue_and_allows_completion():
 r=m.WriteVisibilityLedger();i=identity();r.accept(i);r.fault(4)
 with pytest.raises(m.Rejected):r.accept(identity(1))
 assert not r.reset_allowed();r.issue(i,500);r.acknowledge(i,2000)
 with pytest.raises(m.Rejected):r.retire_visible(i,8000)
 r.retire_visible(i,9000);assert r.reset_allowed()

def test_additive_read_write_quiescence_and_no_reservation_reuse():
 spec=importlib.util.spec_from_file_location('base_recovery_write_test',P.parent/'w17_window_fault_recovery_model.py')
 base=importlib.util.module_from_spec(spec);sys.modules[spec.name]=base;spec.loader.exec_module(base)
 reads=base.RecoveryModel();reads.fault(4);base.model_only_fence(reads)
 writes=m.WriteVisibilityLedger();i=identity();writes.accept(i);writes.issue(i,0);writes.acknowledge(i,1000);writes.fault(4)
 assert reads.can_restart() and not m.recovery_can_restart(reads,writes)
 writes.retire_visible(i,8000);assert m.recovery_can_restart(reads,writes)
 assert not reads.rtl_admission() and not writes.rtl_admission()
 # A later instance of the same owner may not reuse a retired ticket.
 writes.frozen=False
 with pytest.raises(m.Rejected):writes.accept(i)
