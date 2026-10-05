from pathlib import Path
import sys,itertools
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w2_nc6_reset_quarantine as q
ALL=dict(stop=True,provider=True,reverse=True,reset=True,quiet=True)
@pytest.mark.parametrize('flags',list(itertools.product([False,True],repeat=5)))
def test_exact_fence_conjunction(flags):
 c=q.ResetContract();kw=dict(zip(ALL,flags))
 if all(flags):c.rearm(**kw);assert not c.quarantined
 else:
  with pytest.raises(q.Refusal):c.rearm(**kw)
  assert c.quarantined

def live():
 c=q.ResetContract();c.rearm(**ALL);key=(1,44,3,False);c.accept(key);return c,key

def test_r6_debt_is_preserved_across_destructive_local_reset():
 c,k=live();c.reset();c.check()
 assert c.external=={k} and c.orphans=={k} and not c.local
 with pytest.raises(q.Refusal):c.consume(k)
 with pytest.raises(q.Refusal):c.rearm(**ALL)
 with pytest.raises(q.Refusal):c.accept(k)
 c.provider_retire(k);c.rearm(**ALL);c.check();assert not c.external

def test_omitted_reset_orphan_is_fatal_mutant():
 c,k=live();c.reset();c.orphans.clear()
 with pytest.raises(q.Refusal):c.check()

def test_external_debt_cleared_by_local_reset_is_fatal_mutant():
 c,k=live();c.reset();c.external.clear()
 with pytest.raises(q.Refusal):c.check()

def test_ordinary_retirement_still_conserves():
 c,k=live();c.consume(k);c.check();assert not c.external

def test_stale_return_cannot_retire_new_generation():
 c,k=live();c.reset();c.provider_retire(k);c.rearm(**ALL)
 newer=(1,44,4,False);c.accept(newer)
 with pytest.raises(q.Refusal):c.consume(k)
 assert newer in c.external

def test_reset_has_no_new_physical_state_and_no_latency_fit():
 m=q.model();assert m['storage']['added_bits']==0 and m['storage']['codewords']==219
 assert m['reset']['changed_physical_bits']==[0,1,2,71]
 assert m['latency']['healthy_request_II_same_client']==19
 assert m['rearm']['edges']==1 and m['control_price']['max_added_gate_depth_bound']==9

def test_actual_rtl_copies_have_exact_quarantine_and_fence_paths():
 src=q.sources();p=src['ot_w2_nc6_protected_completion_reset_quarantine.sv'];s=src['ot_w2_nc6_coded_secondary_reset_quarantine.sv']
 assert 'OPT_RESET_QUARANTINE=0' in p and 'OPT_RESET_QUARANTINE=0' in s
 assert 'global_index(w)==132)?44\'d1:44\'d0' in s
 assert '.OPT_RESET_QUARANTINE(OPT_RESET_QUARANTINE)' in p
 assert '!p_rsp_v&&!p_wr_done_v' in p and '!(|c_req_v)' in p
 assert 'fault=integrity_bad||payload[36][0]||logic_fault' in s
 assert 'normal_permit=!fault&&!repair_busy' in s
 assert 'rearm_v&&rearm_ready' in s
 assert 'provider_fenced&&reverse_fenced&&reset_fenced' in s
 assert 'else if(rearm_v&&rearm_ready)' in s

def test_defaultoff_is_textual_original_behavior_except_namespace():
 src=q.sources()
 assert q.PRIMARY.read_text().count('localparam integer NW=182')==src['ot_w2_nc6_protected_completion_reset_quarantine.sv'].count('localparam integer NW=182')==1
 assert 'OPT_PROTECTION!=0&&rst_n' in src['ot_w2_nc6_coded_secondary_reset_quarantine.sv']
