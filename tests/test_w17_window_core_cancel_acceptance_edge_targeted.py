"""Target selection/prerequisite/reuse-scope controls. No HDL execution."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_acceptance_edge_first_run as first
import w17_window_core_cancel_acceptance_edge_remaining_run as remaining
REC=ROOT/'results/uarch/w17_window_core_cancel_acceptance_edge_targeted_20261002'
@pytest.fixture(scope='module')
def plans():return first.validate(REC/'first_plan_r2/plan.json'),remaining.validate(REC/'remaining_plan_r2/plan.json')

def test_exact_partition_no_baseline_work_and_all_original_checks_retained(plans):
 f,r=plans;full=json.loads((ROOT/'results/uarch/w17_window_core_cancel_acceptance_edge_20261002/plan_r3/plan.json').read_text())
 assert f['jobs']==full['jobs'][1:2] and r['jobs']==full['jobs'][2:]
 assert f['source_files_sha256']==r['source_files_sha256']==full['source_files_sha256']
 assert f['source_geometry']==r['source_geometry']==full['source_geometry']
 assert f['historical_baseline']==r['historical_baseline']
 for p in plans:
  assert not p['binary_reuse'] and p['historical_baseline']['binary_reused'] is False
  assert p['historical_baseline']['positive_cases']==23
  assert p['historical_baseline']['new_bench_inverse_insertion_sha256']==p['historical_baseline']['original_bench_sha256']
  assert all(j['label']!='baseline' for j in p['jobs'])
  b=p['budget'];assert b['compile_shared_seconds']+b['runtime_shared_seconds']+b['supervision_reserve_seconds']==b['whole_seconds']
 assert f['caps']['RuntimeMaxSec']==720 and r['caps']['RuntimeMaxSec']==2250

@pytest.mark.parametrize('value',[None,{}, {'status':'NOT_REVIEWED'}])
def test_remaining_failclosed_without_reviewed_first_PASS(plans,value):
 with pytest.raises(ValueError,match='first-control PASS'):remaining.first_dependency({'first_control_dependency':value},plans[1])

def test_remaining_no_GO_claim_or_build_without_first_dependency(plans,tmp_path,monkeypatch):
 p=plans[1];plan=REC/'remaining_plan_r2/plan.json';g=json.loads((plan.parent/'parent_GO_template.json').read_text());g['status']=remaining.STATUS
 calls=[]
 monkeypatch.setattr(remaining,'validate',lambda *a:p);monkeypatch.setattr(remaining.base,'git',lambda *a:json.dumps(g))
 monkeypatch.setattr(remaining.base,'claim_go',lambda *a:calls.append(a))
 a=SimpleNamespace(out=str(tmp_path/'out'),plan=str(plan),unit='mock',go_commit='a'*40,go_path='pending')
 assert remaining.launch(a)==1 and not calls
 assert 'first-control PASS' in json.loads((tmp_path/'out/record.json').read_text())['error']

def test_first_control_starts_fresh_frontend_only_and_preserves_failure(plans,tmp_path,monkeypatch):
 p=plans[0];out=tmp_path/'out';out.mkdir();a=SimpleNamespace(out=str(out),plan=str(REC/'first_plan_r2/plan.json'),unit='mock',go_commit='a'*40,go_path='none')
 monkeypatch.setattr(first,'owned_output',lambda *a:out);monkeypatch.setattr(first,'validate',lambda *a:p);monkeypatch.setattr(first,'validate_GO',lambda *a:None);monkeypatch.setattr(first,'caps_receipt',lambda *a:{'kernel_cgroup':'mock'})
 calls=[]
 def fail(command,*a):calls.append(command);raise RuntimeError('mock cap refusal')
 monkeypatch.setattr(first.base,'supervised',fail)
 assert first.worker(a)==1 and len(calls)==1 and '--cc' in calls[0]
 assert '/physical_QE_gate/' in ' '.join(calls[0])
 assert not (out/'baseline').exists() and not (out/'PC_advance').exists()
 assert json.loads((out/'record.json').read_text())['stage']=='physical_QE_gate/frontend'

def test_original_bench_counter_is_monotone_for_historical_zero_acceptance_scope():
 text=(ROOT/first.edge.OLD).read_text()
 assert text.count('qe_accepts++;')==1 and text.count('qe_accepts=0')==1
 assert 'qe_accepts--' not in text and 'qe_accepts=1' not in text
 assert 'if(qe_accepts!=0 || terminals!=0 || vm_stores!=0)' in text
 review=json.loads((ROOT/'results/rtl/w17_window_core_full27_terminal_review_20261002/record.json').read_text())
 closed=json.loads((Path(review['output'])/'baseline/phase_closed.json').read_text())
 for case,step in zip(closed['job']['cases'],closed['steps'][1:]):
  if case['args'] in (['+CUT=ISSUE'],['+CUT=GO']):
   log=Path(step['log']).read_text();assert ' qe=0 terminal=0 vm=0 ' in log
 assert (ROOT/first.edge.NEW).read_text().replace(first.edge.INSERT,'',1)==text

@pytest.mark.parametrize('module,part',[(first,'first'),(remaining,'remaining')])
def test_old_full27_GO_is_not_targeted_authorization(plans,tmp_path,monkeypatch,module,part):
 p=plans[0 if part=='first' else 1];old=json.loads((ROOT/'results/uarch/w17_window_core_cancel_acceptance_edge_20261002/plan_r3/parent_GO_template.json').read_text());old['status']='PARENT_ACTUAL_CORE_ACCEPTANCE_EDGE_FRESH_FULL27_SINGLE_GO'
 monkeypatch.setattr(module.base,'git',lambda *a:json.dumps(old))
 a=SimpleNamespace(plan=str(REC/f'{part}_plan_r2/plan.json'),go_commit='a'*40,go_path='old')
 with pytest.raises(ValueError,match='GO field status'):module.validate_GO(a,p)
