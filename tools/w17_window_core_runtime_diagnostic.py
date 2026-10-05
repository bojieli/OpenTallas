#!/usr/bin/env python3
"""Fresh-GO single diagnostic of EXACT retained binary; no compiler or RTL edits."""
import sys,json,hashlib,subprocess,shutil,re,os,time,resource,argparse,socket,signal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];TOOL=Path(__file__).resolve()
import w17_window_core_cancel_guard_reuse_phase_run as prior
base=prior.base
RUN=Path('/tmp/opentallas-core-guard-reuse-campaign-result-20261002-r2')
BINARY=RUN/'baseline/obj/Vtb';EXPECTED_BINARY='5bc38ebe74a3d8a5af078a5cca9107a4599ccf7b9712ca783a945a583d9ba6a6'
STATUS='PARENT_ACTUAL_CORE_RETAINED_BINARY_STARTUP_DIAGNOSTIC_SINGLE_GO'
CAPS={'MemoryMax':34359738368,'MemorySwapMax':0,'CPUAffinity':[30,31],'LimitFSIZE':1073741824,'LimitCORE':0,'RuntimeMaxSec':60,'KillMode':'control-group','KillSignal':9,'OOMPolicy':'stop'}
BUDGET={'diagnostic_wall_seconds':10,'reserve_seconds':50,'whole_seconds':60,'aggregate_output_bytes':8589934592,'compiler_invocations':0,'binary_invocations':1,'automatic_retries':0,'diagnostic_ptrace_child_only':True}
OBS=ROOT/'tools/w17_window_core_runtime_gdb_observe.py'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def artifact():
 plan=prior.plan_object();progress=json.loads((RUN/'progress_at_failure.json').read_text());record=json.loads((RUN/'record.json').read_text());terminal=json.loads((RUN/'service_receipt.json').read_text());binary=json.loads((RUN/'baseline/binary_receipt.json').read_text())
 if record['stage']!='baseline/runtime_0' or 'stage_time_cap' not in record['error'] or terminal['returncode']!=1 or 'MainPID=0' not in terminal['terminal']:raise ValueError('retained terminal scope')
 if binary!={'sha256':EXPECTED_BINARY,'bytes':105489464} or sha(BINARY)!=EXPECTED_BINARY:raise ValueError('compiled binary identity')
 if len(progress['steps'])!=1 or progress['steps'][0]['returncode']!=0 or progress['steps'][0]['log_sha256']!=sha(RUN/'baseline/CXX.log'):raise ValueError('actual successful CXX receipt')
 expected_command=[x.format(out=str(RUN)) for x in plan['jobs'][0]['CXX_command']]
 if progress['steps'][0]['command']!=expected_command:raise ValueError('CXX provenance command')
 snapshot=json.loads((RUN/'baseline/snapshot_sha256.json').read_text())
 for p,h in plan['source_files_sha256'].items():
  if snapshot.get(p)!=h or sha(RUN/'baseline/sources'/p)!=h:raise ValueError('compiled source snapshot '+p)
 if snapshot.get('tb.sv')!=plan['source_files_sha256']['rtl/test/w17_window_core_cancel_join_r8/tb.sv']:raise ValueError('compiled bench alias')
 names=['record.json','service_receipt.json','baseline/binary_receipt.json','baseline/CXX.log','baseline/snapshot_sha256.json','baseline/frontend_transfer.json','progress_at_failure.json','first_failure_stage.json','resource_samples.jsonl']
 return {'binary_path':str(BINARY),'binary_sha256':EXPECTED_BINARY,'binary_bytes':105489464,'retained_run_receipt_sha256':{p:sha(RUN/p) for p in names},'source_files_sha256':plan['source_files_sha256'],'compiled_CXX_wall_seconds':progress['compile_shared_wall_seconds'],'original_generated_profile':plan['profile_reuse'],'final_scope_cases_and_mutants':[{k:j[k] for k in ('label','mutation','cases')} for j in plan['jobs']],'geometry':plan['source_geometry'],'prior_GO':record['GO_commit']}
def plan_object():
 a=artifact();path=shutil.which('gdb')
 if not path:raise ValueError('native GDB missing; no fallback')
 path=str(Path(path).resolve());version=subprocess.check_output([path,'--version'],text=True).splitlines()[0]
 command=[path,'-nx','-nh','--batch','--return-child-result','-ex','set pagination off','-ex','set confirm off','-ex','set disable-randomization off','-ex','set breakpoint pending off','-ex','python exec(open('+repr(str(OBS))+').read())','--args',str(BINARY),'+CUT=ISSUE']
 return {'status':'PREPARED_NOT_GO','runner_sha256':sha(TOOL),'observer_sha256':sha(OBS),'artifact':a,'gdb':{'path':path,'sha256':sha(path),'version':version},'command':command,'environment_added':{'OT_CORE_DIAG_TRACE':'{out}/progress.jsonl'},'caps':CAPS,'budget':BUDGET,'target_hostname':socket.gethostname(),'observer_scope':'GDB launches ONLY fresh own child, symbol breakpoints/return observations; no existing-process attach. Binary file SHA unchanged. Timing includes debugger overhead; diagnostic not27-case qualification. No DUT variables, clocks, reset,go,payload or expectations changed.','symbols_required':['main','Vtb::Vtb(VerilatedContext*, char const*)','Vtb::eval_step()','Vtb___024root___eval_static(Vtb___024root*)','Vtb___024root___eval_initial(Vtb___024root*)','Vtb___024root___eval_settle(Vtb___024root*)','Vtb___024root___eval(Vtb___024root*)','Vtb::nextTimeSlot()'],'cycle_watchdog':'Original fixture4096 suffix/250000 overall cycles remains byteidentical. Mark up to64 nextTimeSlot returns and16 eval entries; native x86-64 uint64 return RAX is read only.','full27case_scope_preserved':True,'runtime_qualification':False,'physical_provider':False,'fulltoken':False}
def prepare(out):
 p=plan_object();out=Path(out);out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',p);write(out/'parent_GO_template.json',{'status':'PENDING_NOT_AUTHORIZATION','requested_status':STATUS,'plan_sha256':sha(out/'plan.json'),'runner_sha256':sha(TOOL),'artifact_digest':base.digest(p['artifact']),'command_digest':base.digest(p['command']),'observer_sha256':sha(OBS),'caps':CAPS,'budget':BUDGET});return p
def validate(path):
 p=json.loads(Path(path).read_text())
 if p!=plan_object():raise ValueError('plan/binary/source/tool/resource identity')
 return p
def go(a,p):
 if not re.fullmatch('[0-9a-f]{40}',a.go_commit or ''):raise ValueError('fresh committed GO required')
 g=json.loads(base.git('show',a.go_commit+':'+a.go_path))
 for k,v in {'status':STATUS,'requested_status':STATUS,'plan_sha256':sha(a.plan),'runner_sha256':sha(TOOL),'artifact_digest':base.digest(p['artifact']),'command_digest':base.digest(p['command']),'observer_sha256':sha(OBS),'caps':CAPS,'budget':BUDGET}.items():
  if g.get(k)!=v:raise ValueError('GO binding '+k)
 if base.git('status','--porcelain').strip():raise ValueError('clean diagnostic worktree required')
def caps(unit):
 raw=subprocess.check_output(['systemctl','--user','show',unit]+['--property='+k for k in ['ControlGroup','MemoryMax','MemorySwapMax','CPUAffinity','LimitFSIZE','LimitCORE','RuntimeMaxUSec','KillMode','KillSignal','OOMPolicy']],text=True);got=dict(l.split('=',1) for l in raw.splitlines() if '=' in l)
 for k,v in CAPS.items():
  if k=='RuntimeMaxSec':
   if got['RuntimeMaxUSec'] not in ('1min','60000000'):raise ValueError('whole cap')
  elif k=='CPUAffinity':
   if base.parse_cpu_set(got[k])!=v:raise ValueError('CPU cap')
  elif got.get(k)!=str(v):raise ValueError('actual cap '+k)
 rel=next(l.split('::',1)[1] for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::'));cg=Path('/sys/fs/cgroup')/rel.lstrip('/')
 if got['ControlGroup']!=rel or (cg/'memory.max').read_text().strip()!=str(CAPS['MemoryMax']) or (cg/'memory.swap.max').read_text().strip()!='0' or sorted(os.sched_getaffinity(0))!=[30,31] or resource.getrlimit(resource.RLIMIT_FSIZE)!=(1073741824,1073741824):raise ValueError('kernel caps')
 return {'systemd':got,'kernel_cgroup':str(cg)}
def cleanup_own_children(cg):
 for text in (Path(cg)/'cgroup.procs').read_text().splitlines():
  pid=int(text)
  if pid==os.getpid():continue
  try:
   rel=next(l.split('::',1)[1] for l in Path('/proc',text,'cgroup').read_text().splitlines() if l.startswith('0::'))
   if (Path('/sys/fs/cgroup')/rel.lstrip('/')).resolve()==Path(cg).resolve():os.kill(pid,signal.SIGKILL)
  except (ProcessLookupError,FileNotFoundError):pass

def classify(rows):
 stages={v['stage'] for v in rows};slots=[v['raw_rax_uint64'] for v in rows if v['stage']=='NEXT_SIMULATION_SLOT_RETURN']
 if 'DUT_EVAL_ENTER' in stages:return {'progress':'DUT_EVALUATION_REACHED','next_simulation_slots':slots,'DUT_eval_markers':sum(v['stage']=='DUT_EVAL_ENTER' for v in rows)}
 if 'EVAL_STEP_ENTER' in stages:return {'progress':'CONSTRUCTION_FINISHED_INITIALIZATION_IN_PROGRESS','next_simulation_slots':slots}
 if 'CONSTRUCTOR_ENTER' in stages:return {'progress':'MODEL_CONSTRUCTION_ENTERED_NO_COMPLETION_WITNESS','next_simulation_slots':slots}
 return {'progress':'NO_MODEL_START_WITNESS','next_simulation_slots':slots}

def worker(a):
 out=Path(a.out);steps=[];error=None;cap=None
 try:
  p=validate(a.plan);go(a,p);cap=caps(a.unit);write(out/'caps_before_diagnostic.json',cap);base.BUDGET['generated_output_total_bytes']=BUDGET['aggregate_output_bytes'];os.environ['OT_CORE_DIAG_TRACE']=str(out/'progress.jsonl')
  steps.append(base.supervised(p['command'],out/'diagnostic.log',10,out))
 except BaseException as e:error=repr(e)
 finally:
  if cap:cleanup_own_children(cap['kernel_cgroup'])
  rows=[]
  if (out/'progress.jsonl').exists():
   for line in (out/'progress.jsonl').read_text().splitlines():
    try:rows.append(json.loads(line))
    except ValueError:pass
  write(out/'record.json',{'verdict':'DIAGNOSTIC_TERMINAL_NOT_QUALIFICATION','error':error,'steps':steps,'progress':classify(rows),'binary_sha256_after':sha(BINARY),'binary_unchanged':sha(BINARY)==EXPECTED_BINARY,'runtime_qualification':False,'full27scope_qualification':False,'no_retry':True,'physical_provider':False,'fulltoken':False})
 return 1 if error or not steps or steps[0]['returncode']!=0 else 0

def launch(a):
 out=Path(a.out);out.mkdir(parents=True,exist_ok=False);stage='validate'
 try:
  p=validate(a.plan);go(a,p)
  if not re.fullmatch('w17-recovery-runtime-diag-[A-Za-z0-9_-]+',a.unit or ''):raise ValueError('fresh diagnostic unit')
  write(out/'host_admission.json',prior.host_admission(out));claim=base.claim_go(a.go_commit);write(claim/'receipt.json',{'unit':a.unit,'out':str(out),'plan_sha256':sha(a.plan)})
  props=['MemoryMax=34359738368','MemorySwapMax=0','CPUAffinity=30 31','LimitFSIZE=1073741824','LimitCORE=0','RuntimeMaxSec=60','KillMode=control-group','KillSignal=9','OOMPolicy=stop','Nice=10']
  cmd=['systemd-run','--user','--wait','--pipe','--unit='+a.unit]+['--property='+v for v in props]+['--working-directory='+str(ROOT),sys.executable,str(TOOL),'--worker','--plan',str(Path(a.plan).resolve()),'--out',str(out.resolve()),'--unit',a.unit,'--go-commit',a.go_commit,'--go-path',a.go_path]
  write(out/'launch.json',{'command':cmd,'plan_sha256':sha(a.plan),'GO_commit':a.go_commit,'compiler_invocations':0,'binary_invocations':1});stage='service'
  with (out/'service.log').open('x') as log,(out/'resource_samples.jsonl').open('x') as sample:
   child=subprocess.Popen(cmd,stdout=log,stderr=subprocess.STDOUT);start=time.monotonic()
   while child.poll() is None:
    sample.write(json.dumps(prior.sample(a.unit))+'\n');sample.flush()
    if time.monotonic()-start>90:subprocess.run(['systemctl','--user','stop',a.unit],check=False,timeout=10);child.terminate();child.wait(timeout=10);raise ValueError('outer terminal deadline')
    time.sleep(.25)
   sample.flush();os.fsync(sample.fileno())
  state=subprocess.check_output(['systemctl','--user','show',a.unit,'--property=MainPID','--property=Result','--property=ExecMainStatus','--property=ActiveState'],text=True);write(out/'service_receipt.json',{'returncode':child.returncode,'terminal':state,'outside_worker_cgroup':True})
  journal=subprocess.run(['journalctl','--user','-u',a.unit,'--no-pager','-o','short-iso-precise'],capture_output=True,text=True);(out/'service_journal.txt').write_text(journal.stdout+journal.stderr)
  if not (out/'record.json').exists():write(out/'record.json',{'verdict':'DIAGNOSTIC_SERVICE_TERMINAL_WORKER_RECORD_ABSENT','terminal':state,'no_retry':True,'runtime_qualification':False})
  return child.returncode
 except BaseException as e:
  if not (out/'record.json').exists():write(out/'record.json',{'verdict':'FAIL_CLOSED_NO_DIAGNOSTIC_LAUNCH','stage':stage,'error':repr(e),'no_retry':True})
  return 1
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true');ap.add_argument('--worker',action='store_true');ap.add_argument('--out',required=True);ap.add_argument('--plan');ap.add_argument('--unit');ap.add_argument('--go-commit');ap.add_argument('--go-path');a=ap.parse_args()
 if a.prepare:prepare(a.out)
 else:raise SystemExit(worker(a) if a.worker else launch(a))
