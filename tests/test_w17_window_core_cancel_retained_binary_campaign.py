"""Native campaign admission/reuse controls. No compiler or DUT execution."""
import copy,json,sys,shutil
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_retained_binary_campaign as r
PLAN=ROOT/'results/uarch/w17_window_core_cancel_retained_binary_campaign_20261002/plan_r1/plan.json'

@pytest.fixture(scope='module')
def plan():return r.validate(PLAN)

def test_full_scope_exact_sources_cases_mutations(plan):
 old=r.compiled.prior.plan_object()
 assert plan['source_files_sha256']==old['source_files_sha256'] and len(plan['source_files_sha256'])==163
 assert plan['source_geometry']==old['source_geometry']
 for actual,original in zip(plan['jobs'],old['jobs']):
  assert actual['label']==original['label'] and actual['mutation']==original['mutation']
  assert [{k:v for k,v in c.items() if k!='seconds'} for c in actual['cases']]==[{k:v for k,v in c.items() if k!='seconds'} for c in original['cases']]
 assert len(plan['jobs'])==5 and len(plan['jobs'][0]['cases'])==23 and sum(len(j['cases']) for j in plan['jobs'])==27
 assert plan['jobs'][0]['binary_reuse'] and 'CXX_command' not in plan['jobs'][0] and 'frontend_command' not in plan['jobs'][0]
 for actual,original in zip(plan['jobs'][1:],old['jobs'][1:]):
  assert actual['frontend_command']==original['frontend_command'] and actual['CXX_command']==original['CXX_command']

def test_finite_budgets_are_reservations_not_native_measurements(plan):
 b=plan['budget'];cases=[c for j in plan['jobs'] for c in j['cases']]
 assert sum(c['seconds'] for c in cases)==710<=b['runtime_shared_seconds']==720
 assert b['compile_shared_seconds']+b['runtime_shared_seconds']+b['supervision_reserve_seconds']==b['whole_seconds']==3600
 assert b['CXX_processes']==4 and b['new_frontend_processes']==4 and b['baseline_CXX_repeats']==0
 assert plan['diagnostic_receipt']['debugger_inclusive_not_native_estimate']
 assert not plan['diagnostic_receipt']['native_other_case_durations_measured']
 assert r.stage_allowance(2400,500,False)==150 and r.stage_allowance(2400,500,True)==150
 with pytest.raises(ValueError):r.stage_allowance(2600,0,False)

@pytest.fixture
def binary(tmp_path):
 original=tmp_path/'original';original.write_bytes(b'mock compiled artifact; never executed')
 return original,{'binary_path':str(original),'binary_sha256':r.sha(original),'binary_bytes':original.stat().st_size}

def test_transfer_hash_closure_never_compiles_or_changes_original(binary,tmp_path):
 original,a=binary;before=original.read_bytes();home=tmp_path/'baseline';home.mkdir()
 step=r.transfer_binary(home,a)
 assert step['process_executed'] is False and step['command']==[] and step['wall_seconds']==0
 assert (home/'obj/Vtb').read_bytes()==before==original.read_bytes()
 assert r.sha(step['log'])==step['log_sha256']
 assert json.loads((home/'binary_transfer.json').read_text())['baseline_CXX_processes']==0

@pytest.mark.parametrize('field,value',[('binary_sha256','0'*64),('binary_bytes',1)])
def test_transfer_refuses_changed_artifact_before_copy(binary,tmp_path,field,value):
 _,a=binary;a[field]=value;home=tmp_path/'baseline';home.mkdir()
 with pytest.raises(ValueError,match='binary identity'):r.transfer_binary(home,a)
 assert not (home/'obj').exists()

@pytest.mark.parametrize('field,value',[('error','semantic failure'),('binary_unchanged',False),('binary_sha256_after','0'*64)])
def test_diagnostic_negative_receipts(tmp_path,monkeypatch,field,value):
 for name in ('record.json','service_receipt.json','diagnostic.log'):
  shutil.copyfile(r.DIAGNOSTIC/name,tmp_path/name)
 p=tmp_path/'record.json';obj=json.loads(p.read_text());obj[field]=value;p.write_text(json.dumps(obj))
 monkeypatch.setattr(r,'DIAGNOSTIC',tmp_path)
 with pytest.raises(ValueError,match='diagnostic binary/result binding'):r.diagnostic_receipt()

def test_old_GO_refused_before_service_or_claim(plan,tmp_path,monkeypatch):
 called=[];monkeypatch.setattr(r,'validate',lambda p:plan)
 old=json.loads((ROOT/'results/uarch/w17_window_core_cancel_guard_reuse_campaign_20261002/plan_r3/parent_GO_template.json').read_text())
 monkeypatch.setattr(r.base,'git',lambda *a:json.dumps(old))
 monkeypatch.setattr(r.base,'claim_go',lambda *a:called.append(a))
 a=SimpleNamespace(out=str(tmp_path/'out'),plan=str(PLAN),unit='w17-recovery-resource-control',go_commit='a'*40,go_path='old')
 assert r.launch(a)==1 and not called
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='GO_validation'

def test_runtime_first_failure_stops_before_mutant_build(plan,binary,tmp_path,monkeypatch):
 p=copy.deepcopy(plan);p['compiled_artifact']=binary[1];out=tmp_path/'run';out.mkdir()
 a=SimpleNamespace(out=str(out),plan=str(PLAN),unit='control',go_commit='a'*40,go_path='none')
 monkeypatch.setattr(r,'owned_output',lambda *a:out)
 monkeypatch.setattr(r,'validate',lambda *a:p);monkeypatch.setattr(r,'validate_GO',lambda *a:None)
 monkeypatch.setattr(r,'caps_receipt',lambda *a:{'kernel_cgroup':'mock'})
 commands=[]
 def cap(command,*args):commands.append(command);raise RuntimeError('stage_time_cap')
 monkeypatch.setattr(r.base,'supervised',cap)
 assert r.worker(a)==1
 assert commands==[[str((out/'baseline/obj/Vtb').resolve()),'+CUT=ISSUE']]
 assert not (out/'physical_QE_gate').exists() and not (out/'baseline/phase_closed.json').exists()
 rec=json.loads((out/'record.json').read_text())
 assert rec['verdict']=='FAIL_RUNTIME_PRESERVED' and rec['stage']=='baseline/runtime_0'
 assert (out/'baseline/obj/Vtb').exists()

@pytest.mark.parametrize('key,value',[('compiled_artifact',{}),('diagnostic_receipt',{}),('budget',{}),('jobs',[])])
def test_pinned_plan_change_refused(plan,tmp_path,monkeypatch,key,value):
 q=copy.deepcopy(plan);q[key]=value;p=tmp_path/'changed.json';p.write_text(json.dumps(q))
 monkeypatch.setattr(r,'plan_object',lambda:plan)
 with pytest.raises(ValueError,match='plan/source'):r.validate(p)

@pytest.mark.parametrize('index',[1,2,3,4])
def test_all_four_mutants_require_exact_fatal_exit_and_clean_caps(plan,index):
 c=plan['jobs'][index]['cases'][0];n=c['fatal_receipt']['line'];marker=c['marker'];src='/fresh/owned/sources'
 text=f'[42] %Fatal: tb.sv:{n}: Assertion failed in tb: {marker}\n%Error: {src}/tb.sv:{n}: Verilog $stop\nAborting...\n'
 clean={k:0 for k in ('max','oom','oom_kill','oom_group_kill')}
 r.base.verify_runtime(c,1,text,clean,src)
 for code,bad,events in [(9,text,clean),(1,text.replace(marker,'wrong-marker'),clean),(1,text,dict(clean,oom_kill=1)),(1,text.replace(src,'/old/sources'),clean)]:
  with pytest.raises(ValueError):r.base.verify_runtime(c,code,bad,events,src)
