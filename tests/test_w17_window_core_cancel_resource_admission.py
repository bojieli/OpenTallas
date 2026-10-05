"""Pure controls: no compiler, service, model payload, or RTL simulation."""
import json,sys,hashlib,shutil
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_resource_phase_run as campaign
import w17_window_core_cancel_frontend_run as profile
import w17_window_core_cancel_source_ports_repair as source
REC=ROOT/'results/uarch/w17_window_core_cancel_contract_fix_20261002'
PLAN=REC/'campaign_plan_r4/plan.json'
PROFILE=REC/'frontend_plan_r4/plan.json'

def args(tmp,plan=PLAN):
 return SimpleNamespace(out=str(tmp/'out'),plan=str(plan),unit='w17-recovery-resource-control',go_commit=None,go_path='none')

def test_header_complete_default_legacy_inverse():
 for kind,count in [('base',224),('fastpp',239)]:
  record,text,original,_=source.generate(kind)
  assert record['ports_forwarded']==count
  ports=source.parse_ports(original[:source.header_end(original)])
  assert 'coll_fault' in {p[2] for p in ports}
  for _,_,name in ports:assert '.'+name+'('+name+')' in text
  begin=text.index('module '+record['module']+'_legacy #(')
  end=text.index('\nendmodule',begin)+len('\nendmodule')
  assert text[begin:end].replace(record['module']+'_legacy',source.NAME,1)==original.rstrip('\n')

@pytest.mark.parametrize('bad',['input wire a, a','input wire a, .bad','bare'])
def test_bad_or_duplicate_ANSI_identity_rejected(bad):
 with pytest.raises(ValueError):source.parse_ports('module m #(parameter integer W=1) ('+bad+');')

def test_wqr_VM_aperture_bitmap_and_freeze_contract():
 tb=(ROOT/'rtl/test/w17_window_core_cancel_join_r7/tb.sv').read_text()
 m=json.loads(campaign.MODEL.read_text());cone=(ROOT/m['runtime_cone_path']).read_text()
 assert '.xr_re(wqr_re), .xr_addr(wqr_addr), .xr_q(wqr_q)' in cone
 assert 'if(core_wqr_re)' in tb and 'if(core_wxr_re)' not in tb
 for token in ['core_coll_fault=0','core_rope_pf_fault=0','core_rom_ffault=0','sink_last_wide','vm_written','VM_SINK_COMMIT','local_edge-start_edge!=43']:
  assert token in tb
 assert '.coll_fault(core_coll_fault)' in tb
 assert m['accounting']['concrete']==269 and m['accounting']['envelope']==278
 for mutation in m['future_mutants'].values():
  s=tb if mutation.get('target')=='bench' else cone[cone.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #('):]
  assert s.count(mutation['old'])==1


def test_phase_caps_scope_and_profile_no_CXX():
 p=campaign.validate(PLAN);q=profile.validate(PROFILE)
 assert len(p['jobs'])==5 and len(p['jobs'][0]['cases'])==23
 assert p['source_geometry']==q['source_geometry']=={'SUN':256,'SUM':64,'BL':16,'IL':8,'NBMAX':192,'CHUNK8':1,'MP':1,'AW':30,'NW':21}
 assert p['caps']['MemoryMax']==32*1024**3 and p['caps']['LimitFSIZE']==1024**3
 assert p['caps']['RuntimeMaxSec']==2400 and q['caps']['RuntimeMaxSec']==600
 assert p['budget']['compile_shared_seconds']+p['budget']['runtime_shared_seconds']+p['budget']['supervision_reserve_seconds']==2400
 assert sum(c['seconds'] for j in p['jobs'] for c in j['cases'])<=26
 assert '--build' not in q['command'] and '--binary' not in q['command']
 assert q['budget']['CXX_compiles']==q['budget']['simulations']==0
 assert len(q['negative_campaign_preserved'])==4

@pytest.mark.parametrize('key,value',[('runner_sha256','0'*64),('source_files_sha256',{}),('caps',{}),('budget',{}),('jobs',[]),('compiler',{})])
def test_changed_plan_rejected(tmp_path,key,value):
 p=json.loads(PLAN.read_text());p[key]=value;bad=tmp_path/'bad.json';bad.write_text(json.dumps(p))
 with pytest.raises(ValueError):campaign.validate(bad)

@pytest.mark.parametrize('used,phase,front,expected',[(0,0,True,300),(0,100,False,350),(2220,0,True,30),(2200,430,False,20)])
def test_shared_and_phase_budgets_never_reset(used,phase,front,expected):
 assert campaign.stage_allowance(used,phase,front)==expected

@pytest.mark.parametrize('used,phase',[(2250,0),(0,450),(2300,451)])
def test_exhausted_budget_stops(used,phase):
 with pytest.raises(ValueError):campaign.stage_allowance(used,phase,False)

@pytest.mark.parametrize('runner,plan',[(campaign,PLAN),(profile,PROFILE)])
def test_missing_GO_preserved_before_claim_service(tmp_path,monkeypatch,runner,plan):
 calls=[];monkeypatch.setattr(runner.base,'claim_go',lambda *a:calls.append(a))
 assert runner.launch(args(tmp_path,plan))==1
 record=json.loads((tmp_path/'out/record.json').read_text())
 assert record['stage']=='GO_validation' and not calls
 assert not (tmp_path/'out/launch.json').exists()
 assert record['verdict']=='FAIL_CLOSED_PRESERVED_NO_BUILD'

def test_existing_output_never_overwritten(tmp_path,monkeypatch):
 out=tmp_path/'out';out.mkdir();(out/'record.json').write_text('IMMUTABLE_FAIL')
 monkeypatch.setattr(campaign.tempfile,'mkdtemp',lambda **k:str(tmp_path/'fallback'))
 (tmp_path/'fallback').mkdir()
 assert campaign.launch(args(tmp_path))==1
 assert (out/'record.json').read_text()=='IMMUTABLE_FAIL'
 assert json.loads((tmp_path/'fallback/record.json').read_text())['stage']=='output_ownership'

def test_worker_cap_refusal_retained_no_compile(tmp_path,monkeypatch):
 a=args(tmp_path);campaign.owned_output(a)
 monkeypatch.setattr(campaign,'validate_GO',lambda *a:None)
 def denied(unit):raise ValueError('memory cap mutant')
 monkeypatch.setattr(campaign,'caps_receipt',denied)
 called=[];monkeypatch.setattr(campaign.base,'supervised',lambda *a:called.append(a))
 assert campaign.worker(a)==1 and not called
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='actual_caps'


def test_frontend_first_failure_blocks_CXX_and_mutants(tmp_path,monkeypatch):
 a=args(tmp_path);campaign.owned_output(a)
 monkeypatch.setattr(campaign,'validate_GO',lambda *a:None)
 monkeypatch.setattr(campaign,'caps_receipt',lambda unit:{'kernel_cgroup':'/unused'})
 called=[]
 def fail(cmd,log,seconds,out):
  called.append(cmd);Path(log).write_text('frontend failed')
  return {'command':cmd,'returncode':9,'wall_seconds':25.5,'log':str(log),'log_sha256':campaign.sha(log)}
 monkeypatch.setattr(campaign.base,'supervised',fail)
 assert campaign.worker(a)==1 and len(called)==1
 assert called[0][0].endswith('verilator') and '--build' not in called[0]
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='baseline/frontend'
 assert not (tmp_path/'out/physical_QE_gate').exists()


def test_exact_fatal_exit_marker_and_clean_cap_policy():
 campaign.base.fatal_site=campaign.fatal_site
 p=json.loads(PLAN.read_text());events={k:0 for k in ('max','oom','oom_kill','oom_group_kill')};directory='/tmp/owned/sources'
 for job in p['jobs'][1:]:
  case=job['cases'][0];site=case['fatal_receipt'];line=site['line']
  text=f"[100] %Fatal: tb.sv:{line}: Assertion failed in tb: {case['marker']}\n%Error: {directory}/tb.sv:{line}: Verilog $stop\nAborting...\n"
  campaign.base.verify_runtime(case,1,text,events,directory)
  for rc,t,e in [(-6,text,events),(2,text,events),(1,text.replace(case['marker'],'generic'),events),(1,text,dict(events,oom=1)),(1,text,None)]:
   with pytest.raises(ValueError):campaign.base.verify_runtime(case,rc,t,e,directory)


def test_all_control_snapshots_exact_mutation(tmp_path):
 p=json.loads(PLAN.read_text());m=json.loads(campaign.MODEL.read_text())
 for j in p['jobs'][1:]:
  src=tmp_path/j['label'];src.mkdir();target=src/m['runtime_cone_path'];target.parent.mkdir(parents=True)
  shutil.copyfile(ROOT/m['runtime_cone_path'],target);shutil.copyfile(ROOT/'rtl/test/w17_window_core_cancel_join_r7/tb.sv',src/'tb.sv')
  chosen=src/'tb.sv' if j['mutation'].get('target')=='bench' else target;old=chosen.read_text()
  campaign.mutate(src,j,m)
  start=0 if j['mutation'].get('target')=='bench' else old.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
  assert chosen.read_text()==old[:start]+old[start:].replace(j['mutation']['old'],j['mutation']['new'],1)
  assert j['cases'][0]['expected']=='FAIL'

def test_source_pin_failure_before_service(tmp_path,monkeypatch):
 original=campaign.base.git
 def wrong(*args):
  data=original(*args)
  return data+b'wrong' if args[0]=='show' and '4e38326' in args[1] else data
 monkeypatch.setattr(campaign.base,'git',wrong)
 called=[];monkeypatch.setattr(campaign.base,'claim_go',lambda *a:called.append(a))
 assert campaign.launch(args(tmp_path))==1 and not called
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='plan_source_validation'


def test_five_stages_share_budget_and_close_only_after_semantics(tmp_path,monkeypatch):
 a=args(tmp_path);campaign.owned_output(a)
 monkeypatch.setattr(campaign,'validate_GO',lambda *a:None)
 monkeypatch.setattr(campaign,'caps_receipt',lambda unit:{'kernel_cgroup':'/unused'})
 monkeypatch.setattr(campaign.base,'read_clean_runtime_events',lambda *a:{k:0 for k in ('max','oom','oom_kill','oom_group_kill')})
 campaign.base.fatal_site=campaign.fatal_site
 plan=json.loads(PLAN.read_text());calls=[];closed=[]
 def simulated_process(cmd,log,seconds,out):
  calls.append((cmd,seconds));home=Path(log).parent
  if Path(log).name=='frontend.log':
   obj=home/'obj';obj.mkdir();(obj/'Vtb.mk').write_text('mock generation');(obj/'Vtb.cpp').write_text('mock source');text='mock frontend';rc=0;wall=10
  elif Path(log).name=='CXX.log':
   (home/'obj/Vtb').write_text('mock binary');text='mock CXX';rc=0;wall=20
  else:
   job=next(j for j in plan['jobs'] if j['label']==home.name);index=int(Path(log).stem.split('_')[1]);case=job['cases'][index];wall=.01
   if case['expected']=='PASS':text=case['marker'];rc=0
   else:
    line=case['fatal_receipt']['line'];text=f"[100] %Fatal: tb.sv:{line}: Assertion failed in tb: {case['marker']}\n%Error: {home.resolve()}/sources/tb.sv:{line}: Verilog $stop\nAborting...\n";rc=1
  Path(log).write_text(text)
  return {'command':cmd,'returncode':rc,'wall_seconds':wall,'log':str(log.resolve()),'log_sha256':campaign.sha(log)}
 def close(out,home,job,steps,plan_sha,go):
  assert len(steps)==len(job['cases'])+1
  for case,step in zip(job['cases'],steps[1:]):campaign.base.verify_runtime(case,step['returncode'],Path(step['log']).read_text(),step['cap_events'],step['runtime_source_directory'])
  campaign.write(home/'phase_closed.json',{'mock':'semantic closure only, no runtime credit'})
  shutil.rmtree(home/'obj');closed.append(home.name)
 monkeypatch.setattr(campaign.base,'supervised',simulated_process);monkeypatch.setattr(campaign.base,'close_and_reclaim',close)
 assert campaign.worker(a)==0 and closed==[j['label'] for j in plan['jobs']]
 assert len(calls)==10+27
 record=json.loads((tmp_path/'out/record.json').read_text());assert record['compile_shared_wall_seconds']==150
 assert [sec for cmd,sec in calls if cmd[0]=='make']==[440]*5
 assert all(not (tmp_path/'out'/label/'obj').exists() for label in closed)


def test_host_headroom_refused_before_GO_consumption(tmp_path,monkeypatch):
 a=args(tmp_path);called=[]
 monkeypatch.setattr(campaign,'validate_GO',lambda *a:None)
 def refuse(out):raise ValueError('disk headroom insufficient')
 monkeypatch.setattr(campaign,'host_admission',refuse);monkeypatch.setattr(campaign.base,'claim_go',lambda *a:called.append(a))
 assert campaign.launch(a)==1 and not called
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='fresh_host_admission'


@pytest.mark.parametrize('key,bad',[('MemoryMax','4294967296'),('MemorySwapMax','1'),('CPUAffinity','0-1'),('LimitFSIZE','268435456'),('RuntimeMaxUSec','3min'),('KillMode','process'),('OOMPolicy','continue')])
def test_actual_cap_property_mutants_refused_before_compile(monkeypatch,key,bad):
 good={k:str(v) for k,v in campaign.CAPS.items() if k not in ('CPUAffinity','RuntimeMaxSec')}
 good.update(CPUAffinity='30 31',RuntimeMaxUSec='40min',ControlGroup='/owned-test');good[key]=bad
 monkeypatch.setattr(campaign.subprocess,'check_output',lambda *a,**k:'\n'.join(k+'='+v for k,v in good.items()))
 with pytest.raises(ValueError):campaign.caps_receipt('w17-recovery-resource-test')


def test_resource_model_exact_runner_caps_and_historical_draft_preserved():
 m=json.loads((ROOT/'results/uarch/w17_window_core_cancel_resource_proposal_20261002/model.json').read_text())
 p=json.loads(PLAN.read_text());q=json.loads(PROFILE.read_text())
 for key in ('MemoryMax','MemorySwapMax','CPUAffinity','RuntimeMaxSec','LimitFSIZE','KillMode','KillSignal','OOMPolicy'):
  assert m['proposed_caps'][key]==p['caps'][key]
 assert m['output_budget']['single_file_bytes']==p['caps']['LimitFSIZE']==q['caps']['LimitFSIZE']
 assert m['output_budget']['aggregate_bytes']==p['budget']['aggregate_output_bytes']==q['budget']['aggregate_output_bytes']
 assert m['time_budget']['compile_phases']==5
 assert m['failed_run']['wall_seconds']==25.459498 and m['failed_run']['peak_RSS_bytes'] is None
 draft=json.loads((ROOT/'results/uarch/w17_window_core_cancel_resource_proposal_20261002/model_draft1.json').read_text())
 assert draft['proposed_caps']['LimitFSIZE']==268435456
