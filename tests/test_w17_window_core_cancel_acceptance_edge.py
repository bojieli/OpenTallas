"""Source edge/prebuild/campaign controls. Compiler and runtime calls are mocked."""
import copy,json,sys
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_acceptance_edge_run as r
PLAN=ROOT/'results/uarch/w17_window_core_cancel_acceptance_edge_20261002/plan_r3/plan.json'
@pytest.fixture(scope='module')
def plan():return r.validate(PLAN)

def test_only_insert_and_old_checks_preserved():
 old=(ROOT/r.edge.OLD).read_text();new=(ROOT/r.edge.NEW).read_text()
 assert new==r.edge.expected() and new.replace(r.edge.INSERT,'',1)==old
 assert new.count('local ACK before actual suffix and logical EMPTY')==old.count('local ACK before actual suffix and logical EMPTY')==1
 assert new.count('registered go cut accepted QE')==2
 assert new.index(r.edge.INSERT)<new.index('qe_accepts++;')<new.index('local ACK before actual suffix and logical EMPTY')

def test_negedge_injection_is_visible_before_acceptance_injected_flag_is_too_late():
 text=(ROOT/r.edge.NEW).read_text()
 task=text.split('task automatic inject();',1)[1].split('endtask',1)[0]
 assert task.index('recover=1;fault_pulse=1;')<task.index('tick();checking=1;injected=1;')
 assert 'wait(core.g_cancel.u_impl.qe_go);@(negedge clk);inject();' in text
 assert 'recover || fault_pulse' in r.edge.INSERT and 'injected' not in r.edge.INSERT

@pytest.mark.parametrize('cut,known,ready,go,mutant,expected',[
 ('GO',True,True,True,True,True),('GO',True,True,True,False,False),
 ('ISSUE',True,True,True,True,True),('PREFIX',True,True,True,True,False),
 ('GO',False,True,True,True,False),('GO',True,False,True,True,False),('GO',True,True,False,True,False)])
def test_composed_source_edge_truth_table(cut,known,ready,go,mutant,expected):
 # Boolean control model only: neither HDL execution nor FPGA proof.
 physical=go if mutant else go and not known
 prohibited=physical and ready and cut in ('ISSUE','GO') and known
 assert prohibited==expected

def test_cases_geometry_mutations_tool_options_exact_and_no_binary_reuse(plan):
 old=json.loads((ROOT/'results/uarch/w17_window_core_cancel_retained_binary_campaign_20261002/plan_r1/plan.json').read_text())
 assert len(plan['source_files_sha256'])==166
 assert all(plan['source_files_sha256'][k]==v for k,v in old['source_files_sha256'].items())
 assert plan['source_geometry']==old['source_geometry'] and len(plan['jobs'][0]['cases'])==23
 for j,o in zip(plan['jobs'],old['jobs']):
  assert j['label']==o['label'] and j['mutation']==o['mutation']
  for c,original in zip(j['cases'],o['cases']):
   assert {k:v for k,v in c.items() if k!='fatal_receipt'}=={k:v for k,v in original.items() if k!='fatal_receipt'}
  assert '--build' not in j['frontend_command'] and '--binary' not in j['frontend_command']
  assert 'binary_reuse' not in j and 'CXX_command' in j
 assert plan['fresh_closure_required'] and not plan['binary_reuse']
 assert plan['budget']['new_frontend_processes']==plan['budget']['CXX_processes']==5
 assert sum(c['seconds'] for j in plan['jobs'] for c in j['cases'])==710
 assert plan['budget']['compile_shared_seconds']+plan['budget']['runtime_shared_seconds']+plan['budget']['supervision_reserve_seconds']==4500

@pytest.mark.parametrize('index',[1,2,3,4])
def test_precise_mutant_fatal_policy(plan,index):
 c=plan['jobs'][index]['cases'][0];n=c['fatal_receipt']['line'];marker=c['marker'];src='/fresh/source'
 text=f'[7000] %Fatal: tb.sv:{n}: Assertion failed in tb: {marker}\n%Error: {src}/tb.sv:{n}: Verilog $stop\nAborting...\n'
 clean={k:0 for k in ('max','oom','oom_kill','oom_group_kill')}
 r.base.verify_runtime(c,1,text,clean,src)
 for code,bad,events in [(9,text,clean),(1,text.replace(marker,'wrong'),clean),(1,text,dict(clean,oom=1))]:
  with pytest.raises(ValueError):r.base.verify_runtime(c,code,bad,events,src)
 if index==1:
  old=json.loads((ROOT/'results/uarch/w17_window_core_cancel_retained_binary_campaign_20261002/plan_r1/plan.json').read_text())['jobs'][1]['cases'][0]['fatal_receipt']['line']
  assert n<old and n<1345

def test_worker_first_process_is_frontend_and_failure_preserved(plan,tmp_path,monkeypatch):
 out=tmp_path/'out';out.mkdir();a=SimpleNamespace(out=str(out),plan=str(PLAN),go_commit='a'*40,go_path='none',unit='mock')
 monkeypatch.setattr(r,'owned_output',lambda *a:out);monkeypatch.setattr(r,'validate',lambda *a:plan);monkeypatch.setattr(r,'validate_GO',lambda *a:None)
 monkeypatch.setattr(r,'caps_receipt',lambda *a:{'kernel_cgroup':'mock'})
 commands=[]
 def refuse(command,*a):commands.append(command);raise RuntimeError('mock frontend refusal')
 monkeypatch.setattr(r.base,'supervised',refuse)
 assert r.worker(a)==1 and len(commands)==1 and '--cc' in commands[0]
 assert not (out/'baseline/obj/Vtb').exists() and not (out/'physical_QE_gate').exists()
 assert json.loads((out/'record.json').read_text())['verdict']=='FAIL_BUILD_PRESERVED'

def test_mocked_all_five_phases_close_and_terminal_has_no_stale_reuse_reference(plan,tmp_path,monkeypatch):
 out=tmp_path/'out';out.mkdir();a=SimpleNamespace(out=str(out),plan=str(PLAN),go_commit='a'*40,go_path='none',unit='mock')
 monkeypatch.setattr(r,'owned_output',lambda *a:out);monkeypatch.setattr(r,'validate',lambda *a:plan);monkeypatch.setattr(r,'validate_GO',lambda *a:None)
 monkeypatch.setattr(r,'caps_receipt',lambda *a:{'kernel_cgroup':'mock'})
 clean={k:0 for k in ('max','oom','oom_kill','oom_group_kill')};monkeypatch.setattr(r.base,'read_clean_runtime_events',lambda *a:clean)
 commands=[]
 def simulate(command,log,*a):
  commands.append(command);home=log.parent;job=next(j for j in plan['jobs'] if j['label']==home.name);code=0;text='MOCK only, no execution\n'
  if log.name=='frontend.log':
   obj=home/'obj';obj.mkdir();(obj/'Vtb.mk').write_text('MOCK');(obj/'Vtb.cpp').write_text('MOCK')
  elif log.name=='CXX.log':(home/'obj/Vtb').write_bytes(b'MOCK never executable')
  else:
   case=next(c for c in job['cases'] if c['args']==command[1:]);text=case['marker']+'\n'
   if case['expected']=='FAIL':
    n=case['fatal_receipt']['line'];text=f"[7000] %Fatal: tb.sv:{n}: Assertion failed in tb: {case['marker']}\n%Error: {home}/sources/tb.sv:{n}: Verilog $stop\nAborting...\n";code=1
  log.write_text(text);return {'command':command,'returncode':code,'wall_seconds':.01,'log':str(log),'log_sha256':r.sha(log)}
 monkeypatch.setattr(r.base,'supervised',simulate)
 assert r.worker(a)==0
 rec=json.loads((out/'record.json').read_text());assert len(rec['phase_receipts'])==5 and len(commands)==37
 assert rec['fresh_closure_required'] and rec['binary_reuse'] is False
 for job in plan['jobs']:
  assert (out/job['label']/'phase_closed.json').exists() and not (out/job['label']/'obj').exists()

def test_old_GO_refused_before_claim_or_service(plan,tmp_path,monkeypatch):
 old=json.loads((ROOT/'results/uarch/w17_window_core_cancel_retained_binary_campaign_20261002/plan_r1/parent_GO_template.json').read_text())
 monkeypatch.setattr(r,'validate',lambda *a:plan);monkeypatch.setattr(r.base,'git',lambda *a:json.dumps(old));calls=[]
 monkeypatch.setattr(r.base,'claim_go',lambda *a:calls.append(a))
 a=SimpleNamespace(out=str(tmp_path/'out'),plan=str(PLAN),go_commit='a'*40,go_path='old',unit='mock')
 assert r.launch(a)==1 and not calls
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='GO_validation'


def test_fatal_site_policy_is_private_to_new_bench():
 import w17_window_recovery_fatal_gate_run as shared
 assert r.base is not shared
 before=shared.fatal_site
 assert r.fatal_site('registered go cut accepted QE')['line']==1261
 assert shared.fatal_site is before
