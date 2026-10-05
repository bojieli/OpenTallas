"""Closure/transfer/admission controls only; no actual CXX or runtime invocation."""
import sys,json,shutil,hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import w17_window_core_cancel_guard_frontend_reuse as reuse
import w17_window_core_cancel_guard_reuse_phase_run as runner
REC=ROOT/'results/uarch/w17_window_core_cancel_guard_reuse_campaign_20261002'
PLAN=REC/'plan_r3/plan.json'

def put(path,obj):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(obj)+'\n')
@pytest.fixture
def closed(tmp_path):
 root=tmp_path/'profile';src=root/'baseline/sources';obj=root/'baseline/obj';src.mkdir(parents=True);obj.mkdir()
 (src/'tb.sv').write_text('mock bench; not executable');(obj/'Vtb.mk').write_text('mock makefile');(obj/'Vtb.cpp').write_text('mock generated text')
 bench='fixture/tb.sv';(src/'fixture').mkdir();shutil.copyfile(src/'tb.sv',src/bench)
 source={bench:reuse.sha(src/bench)};compiler={'wrapper_sha256':'a'*64};command=['fake-frontend','--cc','--Mdir',str(obj)];cap=dict(runner.profile_runner.CAPS)
 (root/'baseline/frontend.log').write_text('mock successful generation\n');(root/'service_journal.txt').write_text('mock journal')
 plan_path=tmp_path/'original_plan.json'
 plan={'command':['fake-frontend','--cc','--Mdir','{out}/baseline/obj'],'compiler':compiler,'source_files_sha256':source,'runner_sha256':'b'*64,'caps':cap};put(plan_path,plan)
 put(root/'record.json',{'verdict':'PASS_FRONTEND_GENERATION_ONLY','CXX_compiles':0,'simulations':0,'GO_commit':'c'*40,'plan_sha256':reuse.sha(plan_path)})
 put(root/'service_receipt.json',{'returncode':0,'worker_record_exists':True,'outside_worker_cgroup':True,'terminal':'Result=success\nMainPID=0\nExecMainStatus=0\nActiveState=inactive\n'})
 actual={k:str(v) for k,v in cap.items() if k not in ('CPUAffinity','RuntimeMaxSec')};actual.update(CPUAffinity='30 31',RuntimeMaxUSec='10min');put(root/'caps_before_frontend.json',{'systemd':actual})
 put(root/'output_owner.json',{'GO_commit':'c'*40,'runner_sha256':'b'*64,'requested_plan':str(plan_path)})
 inv=runner.base.inventory(obj);step={'command':command,'returncode':0,'wall_seconds':100,'log_sha256':reuse.sha(root/'baseline/frontend.log'),'log':str(root/'baseline/frontend.log')}
 put(root/'frontend_closure.json',{'status':'GENERATED_SOURCES_CLOSED_NOT_RUNTIME_PASS','source_pins':source,'files':inv,'inventory_sha256':reuse.digest(inv),'generated_bytes':sum(v['bytes'] for v in inv.values()),'steps':[step]})
 put(root/'baseline/snapshot_sha256.json',{p:reuse.sha(src/p) for p in [bench,'tb.sv']})
 put(root/'resource_samples.jsonl',{'memory.peak':str(6*1024**3),'memory.events':'low 0\nhigh 0\nmax 0\noom 0\noom_kill 0\noom_group_kill 0\n'})
 return root,source,compiler,command,cap,bench

def validate_closed(closed):
 root,source,compiler,command,cap,bench=closed
 return reuse.validate_profile(root,source,compiler,command,cap,runner.base.inventory,bench,'b'*64)


def test_exact_transfer_and_original_closure_immutable(closed,tmp_path):
 receipt=validate_closed(closed);root=closed[0];before=runner.base.inventory(root);home=tmp_path/'owned-baseline';home.mkdir()
 transfer=reuse.transfer(root,home,receipt,runner.base.inventory)
 assert transfer['status']=='PASS_BYTE_EXACT_GENERATED_COPY_NO_FRONTEND'
 assert runner.base.inventory(home/'obj')==receipt['generated_inventory']
 assert runner.base.inventory(root)==before
 assert (home/'frontend.log').read_bytes()==(root/'baseline/frontend.log').read_bytes()

@pytest.mark.parametrize('file,key,value',[
 ('record.json','verdict','FAIL'),('record.json','CXX_compiles',1),('service_receipt.json','returncode',9),('service_receipt.json','terminal','Result=oom-kill\nMainPID=0\nActiveState=failed\nExecMainStatus=9\n'),('frontend_closure.json','source_pins',{}),('frontend_closure.json','inventory_sha256','0'*64),('frontend_closure.json','generated_bytes',1),('output_owner.json','runner_sha256','0'*64),('record.json','GO_commit','d'*40)])
def test_rejected_receipt_or_source_mutants(closed,file,key,value):
 path=closed[0]/file;obj=json.loads(path.read_text());obj[key]=value;put(path,obj)
 with pytest.raises(ValueError):validate_closed(closed)


def test_existing_loop_rejected_even_with_updated_log_hash(closed):
 root=closed[0];log=root/'baseline/frontend.log';log.write_text('%Warning-UNOPTFLAT: rec_stop\n')
 p=root/'frontend_closure.json';c=json.loads(p.read_text());c['steps'][0]['log_sha256']=reuse.sha(log);put(p,c)
 with pytest.raises(ValueError,match='UNOPTFLAT'):validate_closed(closed)


def test_changed_generated_file_and_transfer_race_rejected(closed,tmp_path):
 r=validate_closed(closed);root=closed[0];(root/'baseline/obj/Vtb.cpp').write_text('different')
 with pytest.raises(ValueError,match='generated closure changed'):validate_closed(closed)
 home=tmp_path/'owned';home.mkdir()
 with pytest.raises(ValueError,match='profile changed before transfer'):reuse.transfer(root,home,r,runner.base.inventory)
 assert not (home/'obj').exists()


def test_missing_terminal_and_OOM_events_refused(closed):
 root=closed[0];put(root/'resource_samples.jsonl',{'memory.peak':'1000','memory.events':'max 1\noom 1\noom_kill 1\noom_group_kill 0\n'})
 with pytest.raises(ValueError,match='resource events'):validate_closed(closed)
 (root/'service_receipt.json').unlink()
 with pytest.raises(ValueError,match='not terminal'):validate_closed(closed)


def test_real_closed_plan_all_cases_and_no_baseline_frontend():
 p=runner.validate(PLAN)
 assert len(p['jobs'])==5 and len(p['jobs'][0]['cases'])==23
 assert p['jobs'][0]['frontend_reuse'] is True and not any(j.get('frontend_reuse') for j in p['jobs'][1:])
 assert p['budget']['new_frontend_processes']==4 and p['budget']['CXX_processes']==5 and p['budget']['baseline_frontend_repeats']==0
 assert p['profile_reuse']['prior_GO_commit'].startswith('f56a312b1')
 assert p['profile_reuse']['generated_bytes']>700_000_000 and p['profile_reuse']['observed_cumulative_peak_bytes']>4*1024**3
 assert p['source_geometry']['SUN']==256 and p['source_geometry']['SUM']==64
 assert sum(len(j['cases']) for j in p['jobs'])==27


def test_missing_GO_before_claim_build(tmp_path,monkeypatch):
 called=[];monkeypatch.setattr(runner.base,'claim_go',lambda *a:called.append(a))
 args=SimpleNamespace(out=str(tmp_path/'out'),plan=str(PLAN),unit='w17-recovery-resource-reuse-control',go_commit=None,go_path='none')
 assert runner.launch(args)==1 and not called
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='GO_validation'

@pytest.mark.parametrize('key,value',[('profile_reuse',{}),('dependencies_sha256',{}),('caps',{}),('jobs',[]),('budget',{}),('build_toolchain',{})])
def test_campaign_pin_and_control_changes_refused(tmp_path,key,value):
 p=json.loads(PLAN.read_text());p[key]=value;bad=tmp_path/'bad.json';put(bad,p)
 with pytest.raises(ValueError):runner.validate(bad)


def test_baseline_worker_starts_CXX_not_frontend(tmp_path,monkeypatch):
 args=SimpleNamespace(out=str(tmp_path/'out'),plan=str(PLAN),unit='w17-recovery-resource-reuse-control',go_commit=None,go_path='none')
 runner.owned_output(args);p=json.loads(PLAN.read_text())
 monkeypatch.setattr(runner,'validate',lambda *a:p);monkeypatch.setattr(runner,'validate_GO',lambda *a:None);monkeypatch.setattr(runner,'caps_receipt',lambda *a:{'kernel_cgroup':'/mock'})
 def transfer(profile,home,receipt,inventory):
  (home/'obj').mkdir();(home/'obj/mock').write_text('fake transferred output')
  (home/'frontend.log').write_text('fake closed frontend')
  return {'mock':'transfer, not actual runtime credit'}
 monkeypatch.setattr(runner.reuse,'transfer',transfer);calls=[]
 def fail_CXX(cmd,log,seconds,out):
  calls.append(cmd);Path(log).write_text('simulated build refusal')
  return {'command':cmd,'returncode':1,'wall_seconds':1,'log':str(log),'log_sha256':reuse.sha(log)}
 monkeypatch.setattr(runner.base,'supervised',fail_CXX)
 assert runner.worker(args)==1 and len(calls)==1 and Path(calls[0][0]).name=='make'
 assert json.loads((tmp_path/'out/record.json').read_text())['stage']=='baseline/CXX'
 assert not (tmp_path/'out/physical_QE_gate').exists()
