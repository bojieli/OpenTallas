#!/usr/bin/env python3
"""Fresh-GO frontend generation after guard ingress repair; no CXX or sim."""
import argparse,json,hashlib,subprocess,sys,os,re,time,tempfile,shutil,resource,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import w17_window_recovery_fatal_gate_run as base
MODEL=ROOT/'results/uarch/w17_window_core_cancel_guard_feedback_repair_20261002/model.json'
PROVIDER=ROOT/'results/rtl/w17_window_recovery_candidate_prepared_20261002/record.json'
PROOF=ROOT/'results/uarch/w17_window_core_cancel_join_preparation_r6_20261002/source_edge_proof.json'
PRODUCER='rtl/test/w17_window_actual_producer_cancel_declaration_repaired/ot_hdc_v41x_window_kv_blocks_cancel.sv'
TOOL=Path(__file__).resolve();STATUS='PARENT_ACTUAL_CORE_SU_QE_GUARD_REPAIRED_FRONTEND_SINGLE_GO'
CAPS={'MemoryMax':34359738368,'MemorySwapMax':0,'CPUAffinity':[30,31],'LimitFSIZE':1073741824,'LimitCORE':0,'RuntimeMaxSec':600,'KillMode':'control-group','KillSignal':9,'OOMPolicy':'stop'}
BUDGET={'frontend_seconds':540,'supervision_reserve_seconds':60,'whole_seconds':600,'aggregate_output_bytes':8589934592,'sample_interval_seconds':0.25,'compile_workers_max':2,'CXX_compiles':0,'simulations':0,'automatic_retries':0}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def safe_sha(p):
 try:return sha(p)
 except OSError:return None

def pins():
 m=json.loads(MODEL.read_text());r=json.loads(PROVIDER.read_text());files=dict(m['original_source_sha256'])
 files.update(r['prepared_files_sha256'])
 extras=[m['runtime_cone_path'],m['core_path'],PRODUCER,'rtl/test/w17_window_core_cancel_join_r8/tb.sv',str(MODEL.relative_to(ROOT)),str(PROVIDER.relative_to(ROOT)),str(PROOF.relative_to(ROOT)),
  'tools/w17_window_core_cancel_resource_proposal.py','results/uarch/w17_window_core_cancel_resource_proposal_20261002/model.json','tools/w17_window_core_cancel_guard_feedback_repair.py','tools/w17_window_core_cancel_source_ports_repair.py','tools/w17_window_core_cancel_join_contract_prepare.py','tools/w17_window_core_cancel_join_edge_proof.py','tools/w17_window_recovery_fatal_gate_run.py']
 files.update({p:sha(ROOT/p) for p in extras})
 if files[m['runtime_cone_path']]!=m['runtime_cone_sha256'] or files['rtl/test/w17_window_core_cancel_join_r8/tb.sv']!=m['bench_sha256']:raise ValueError('fixture/cone pin')
 for p,h in files.items():
  data=base.git('show',m['pin']+':'+p) if p in m['original_source_sha256'] else (ROOT/p).read_bytes()
  if hashlib.sha256(data).hexdigest()!=h:raise ValueError('source pin '+p)
 if (ROOT/PRODUCER).read_bytes()!=base.git('show','3625a502b889d3a69aada6796cd9ceb8eefb6810:'+PRODUCER):raise ValueError('producer pin')
 if m['accounting']['concrete']!=269 or m['accounting']['envelope']!=278:raise ValueError('allocation')
 return m,r,files

def host_admission(out):
 mem={l.split(':',1)[0]:l.split(':',1)[1].strip() for l in Path('/proc/meminfo').read_text().splitlines()}
 available=int(mem['MemAvailable'].split()[0])*1024
 free=shutil.disk_usage(out).free;affinity=sorted(os.sched_getaffinity(0))
 host=socket.gethostname()
 if any(x in host.lower() for x in ('pve2','pve3')):raise ValueError('fleet drain forbids new host admission')
 if available<60129542144 or free<17179869184 or not {30,31}.issubset(affinity):raise ValueError('fresh host memory/disk/CPU admission refused')
 return {'hostname':host,'MemAvailable_bytes':available,'disk_free_bytes':free,'launcher_affinity':affinity,'minimum_available_memory_bytes':60129542144,'minimum_disk_free_bytes':17179869184,'owned_PVE2_PVE3_jobs':[]}

def plan_object():
 m,r,files=pins();sources=[p for p in m['original_source_sha256'] if p.endswith(('.sv','.v'))]
 sources+=[m['runtime_cone_path'],PRODUCER]+[p for p in r['future_compile_inputs']['sources'] if Path(p).name!='tb.sv']
 sources=list(dict.fromkeys(sources));compiler=base.compiler()
 # --cc --main --exe --timing is the elaboration/generation part of --binary;
 # deliberately omit --build. Same RTL geometry/options, no CXX process admitted.
 cmd=[compiler['wrapper'],'--cc','--main','--exe','--timing','--assert','--top-module','tb','-j','2','-Wno-fatal','--unroll-count','1','--unroll-limit','131072','--output-split','20000','--output-split-cfuncs','2000','-CFLAGS','-O0','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0','--Mdir','{out}/baseline/obj','-I{out}/baseline/sources/rtl/hdc/v41']+['{out}/baseline/sources/'+p for p in sources]+['{out}/baseline/sources/tb.sv']
 return {'status':'PREPARED_NOT_GO','target_local_hostname':socket.gethostname(),'runner_sha256':sha(TOOL),'model_sha256':sha(MODEL),'compiler':compiler,'source_files_sha256':files,'source_inputs':sources,'command':cmd,'caps':CAPS,'budget':BUDGET,
 'negative_campaign_preserved':m['future_mutants'],'positive_cases_preserved':m['cases'],'campaign_later_gate':'Fresh separate review/GO after observed front-end RAM/time/generated-output closure; no automatic CXX or mutant next stage.',
 'source_geometry':{'SUN':256,'SUM':64,'BL':16,'IL':8,'NBMAX':192,'CHUNK8':1,'MP':1,'AW':30,'NW':21},'prior_closure_reuse':False,'guard_provider':'Synthetic registered producer DRAIN observer; production raw-intent fault interface absent','physical_provider':False,'runtime_qualification':False,'full_program_primary':True,'fulltoken':False}

def prepare(out):
 p=plan_object();out=Path(out);out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',p)
 write(out/'parent_GO_template.json',{'status':'PENDING_NOT_AUTHORIZATION','requested_status':STATUS,'plan_sha256':sha(out/'plan.json'),'runner_sha256':sha(TOOL),'source_digest':base.digest(p['source_files_sha256']),'command_digest':base.digest(p['command']),'caps':CAPS,'budget':BUDGET})
 return p

def validate(path):
 p=json.loads(Path(path).read_text())
 if p!=plan_object():raise ValueError('plan/source/tool/geometry/command/cap changed')
 if '--build' in p['command'] or '--binary' in p['command']:raise ValueError('CXX forbidden in profiling stage')
 return p

def validate_GO(a,p):
 if not re.fullmatch('[0-9a-f]{40}',a.go_commit or ''):raise ValueError('fresh committed GO required')
 g=json.loads(base.git('show',a.go_commit+':'+a.go_path))
 for k,v in {'status':STATUS,'requested_status':STATUS,'plan_sha256':sha(a.plan),'runner_sha256':sha(TOOL),'source_digest':base.digest(p['source_files_sha256']),'command_digest':base.digest(p['command']),'caps':CAPS,'budget':BUDGET}.items():
  if g.get(k)!=v:raise ValueError('GO field '+k)
 if base.git('status','--porcelain').strip():raise ValueError('clean pinned worktree required')


def owned_output(a,worker=False):
 out=Path(a.out)
 if worker:
  if out.is_symlink():raise ValueError('output symlink')
  v=json.loads((out/'output_owner.json').read_text())
  if v!={'runner_sha256':sha(TOOL),'unit':a.unit,'GO_commit':a.go_commit,'requested_plan':str(Path(a.plan).resolve())}:raise ValueError('worker output ownership')
  write(out/'worker_entered.json',{'unit':a.unit,'no_retry':True})
 else:
  out.mkdir(parents=True,exist_ok=False)
  write(out/'output_owner.json',{'runner_sha256':sha(TOOL),'unit':a.unit,'GO_commit':a.go_commit,'requested_plan':str(Path(a.plan).resolve())})
 return out

def refusal(a,out,stage,error):
 if out is None:
  out=Path(tempfile.mkdtemp(prefix='window-core-frontend-refusal-'))
 receipt={'verdict':'FAIL_CLOSED_PRESERVED_NO_BUILD','stage':stage,'error':repr(error),'requested_out':a.out,'receipt_out':str(out.resolve()),'plan_sha256':safe_sha(a.plan),'unit':a.unit,'GO_commit':a.go_commit,'no_retry':True,'physical_provider':False,'runtime_qualification':False}
 if not (out/'record.json').exists():write(out/'record.json',receipt)
 print('Failure receipt: '+str(out/'record.json'),file=sys.stderr)


def caps_receipt(unit):
 fields=['ControlGroup','MemoryMax','MemorySwapMax','CPUAffinity','LimitFSIZE','LimitCORE','RuntimeMaxUSec','KillMode','KillSignal','OOMPolicy']
 raw=subprocess.check_output(['systemctl','--user','show',unit]+['--property='+k for k in fields],text=True)
 got=dict(l.split('=',1) for l in raw.splitlines() if '=' in l)
 for k,v in CAPS.items():
  if k=='RuntimeMaxSec':
   if got.get('RuntimeMaxUSec') not in ('10min','600000000'):raise ValueError('actual whole cap')
  elif k=='CPUAffinity':
   if base.parse_cpu_set(got.get(k,''))!=v:raise ValueError('actual CPU cap')
  elif str(got.get(k))!=str(v):raise ValueError('actual cap '+k)
 if sorted(os.sched_getaffinity(0))!=[30,31] or resource.getrlimit(resource.RLIMIT_FSIZE)!=(1073741824,1073741824):raise ValueError('actual affinity/FSIZE')
 relative=next(l.split('::',1)[1] for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::'));cg=Path('/sys/fs/cgroup')/relative.lstrip('/')
 if got['ControlGroup']!=relative or (cg/'memory.max').read_text().strip()!=str(CAPS['MemoryMax']) or (cg/'memory.swap.max').read_text().strip()!='0':raise ValueError('actual aggregate cgroup')
 return {'systemd':got,'kernel_cgroup':str(cg),'affinity':list(os.sched_getaffinity(0))}


def worker(a):
 out=None;stage='output_ownership';p={};steps=[]
 try:
  out=owned_output(a,True);stage='plan_source_validation';p=validate(a.plan);stage='GO_validation';validate_GO(a,p)
  stage='actual_caps';write(out/'caps_before_frontend.json',caps_receipt(a.unit))
  src=out/'baseline/sources';src.mkdir(parents=True,exist_ok=False);m=json.loads(MODEL.read_text())
  for path,h in p['source_files_sha256'].items():
   target=src/path;target.parent.mkdir(parents=True,exist_ok=True)
   data=base.git('show',m['pin']+':'+path) if path in m['original_source_sha256'] else (ROOT/path).read_bytes()
   if hashlib.sha256(data).hexdigest()!=h:raise ValueError('snapshot mismatch '+path)
   target.write_bytes(data)
  shutil.copyfile(ROOT/'rtl/test/w17_window_core_cancel_join_r8/tb.sv',src/'tb.sv')
  write(out/'baseline/snapshot_sha256.json',{p.relative_to(src).as_posix():sha(p) for p in src.rglob('*') if p.is_file()})
  stage='frontend_generation';base.BUDGET['generated_output_total_bytes']=8589934592
  command=[s.format(out=str(out.resolve())) for s in p['command']]
  step=base.supervised(command,out/'baseline/frontend.log',540,out);steps.append(step)
  if step['returncode']!=0:raise ValueError('frontend nonzero; preserve no retry')
  if '%Warning-UNOPTFLAT:' in (out/'baseline/frontend.log').read_text():raise ValueError('UNOPTFLAT remains; no CXX/runtime readiness')
  obj=out/'baseline/obj';files=base.inventory(obj)
  if any(name.endswith(('.o','.a','.so')) or name=='Vtb' for name in files):raise ValueError('unexpected CXX/binary artifact')
  if 'Vtb.mk' not in files or not any(name.endswith('.cpp') for name in files):raise ValueError('incomplete front-end generated closure')
  for name in files:
   with (obj/name).open('rb') as f:os.fsync(f.fileno())
  write(out/'frontend_closure.json',{'status':'GENERATED_SOURCES_CLOSED_NOT_RUNTIME_PASS','files':files,'inventory_sha256':base.digest(files),'source_pins':p['source_files_sha256'],'steps':steps,'generated_bytes':sum(v['bytes'] for v in files.values()),'no_reclamation':'Keep generated sources for independent review; CXX requires freshGO.'})
  write(out/'record.json',{'verdict':'PASS_FRONTEND_GENERATION_ONLY','steps':steps,'plan_sha256':sha(a.plan),'GO_commit':a.go_commit,'CXX_compiles':0,'simulations':0,'physical_provider':False,'runtime_qualification':False,'fulltoken':False});return 0
 except BaseException as e:
  refusal(a,out,stage,e);return 1


def sample(unit):
 row={'monotonic_seconds':time.monotonic()}
 try:
  relative=subprocess.check_output(['systemctl','--user','show',unit,'--property=ControlGroup','--value'],text=True,stderr=subprocess.DEVNULL,timeout=2).strip()
  cg=Path('/sys/fs/cgroup')/relative.lstrip('/')
  if not relative:raise ValueError('unit cgroup not yet present')
  for name in ['memory.current','memory.peak','memory.events','cpu.stat','pids.current']:
   try:row[name]=(cg/name).read_text().strip()
   except OSError:row[name]=None
 except (OSError,ValueError,subprocess.SubprocessError):row['cgroup_unavailable']=True
 return row


def launch(a):
 out=None;stage='output_ownership'
 try:
  out=owned_output(a);stage='plan_source_validation';p=validate(a.plan);stage='GO_validation';validate_GO(a,p)
  if not re.fullmatch(r'w17-recovery-frontend-[A-Za-z0-9_-]+',a.unit or ''):raise ValueError('fresh frontend user-unit')
  stage='fresh_host_admission';write(out/'host_admission.json',host_admission(out))
  if socket.gethostname()!=p['target_local_hostname']:raise ValueError('reviewed local hostname mismatch')
  stage='fresh_GO_claim';claim=base.claim_go(a.go_commit);write(claim/'receipt.json',{'unit':a.unit,'out':str(out.resolve()),'plan_sha256':sha(a.plan)})
  props=['MemoryMax=34359738368','MemorySwapMax=0','CPUAffinity=30 31','LimitFSIZE=1073741824','LimitCORE=0','RuntimeMaxSec=600','KillMode=control-group','KillSignal=9','OOMPolicy=stop','Nice=10']
  command=['systemd-run','--user','--wait','--pipe','--unit='+a.unit]+['--property='+x for x in props]+['--working-directory='+str(ROOT),sys.executable,str(TOOL),'--worker','--plan',str(Path(a.plan).resolve()),'--out',str(out.resolve()),'--unit',a.unit,'--go-commit',a.go_commit,'--go-path',a.go_path]
  write(out/'launch.json',{'command':command,'plan_sha256':sha(a.plan),'GO_commit':a.go_commit,'automatic_next_stage':False})
  stage='single_service'
  with (out/'service.log').open('x') as log,(out/'resource_samples.jsonl').open('x') as telemetry:
   child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT);started=time.monotonic()
   while child.poll() is None:
    row=sample(a.unit)
    progress=sorted(out.glob('*/*_started.json'),key=lambda x:x.stat().st_mtime_ns)
    row['active_stage']=json.loads(progress[-1].read_text()) if progress else None
    try:row['supervised_command_stage']=json.loads((out/'active_stage.json').read_text())
    except (OSError,ValueError):row['supervised_command_stage']=None
    telemetry.write(json.dumps(row)+'\n');telemetry.flush()
    if time.monotonic()-started>CAPS['RuntimeMaxSec']+30:
     subprocess.run(['systemctl','--user','stop',a.unit],timeout=10,check=False);child.terminate();child.wait(timeout=10);raise ValueError('outside monitor terminal deadline; owned unit stopped, no retry')
    time.sleep(.25)
   telemetry.write(json.dumps(sample(a.unit))+'\n');telemetry.flush();os.fsync(telemetry.fileno())
  terminal=subprocess.check_output(['systemctl','--user','show',a.unit,'--property=ActiveState','--property=MainPID','--property=Result','--property=ExecMainStatus','--property=CPUUsageNSec'],text=True)
  journal=subprocess.run(['journalctl','--user','-u',a.unit,'--no-pager','-o','short-iso-precise'],capture_output=True,text=True)
  (out/'service_journal.txt').write_text(journal.stdout+journal.stderr)
  write(out/'service_receipt.json',{'returncode':child.returncode,'terminal':terminal,'worker_record_exists':(out/'record.json').exists(),'outside_worker_cgroup':True})
  if not (out/'record.json').exists():write(out/'record.json',{'verdict':'FAIL_RESOURCE_OR_SERVICE_TERMINAL_WORKER_RECORD_ABSENT','terminal':terminal,'runtime_qualification':False,'physical_provider':False,'no_retry':True})
  return child.returncode
 except BaseException as e:
  refusal(a,out,stage,e);return 1
if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--prepare',action='store_true');ap.add_argument('--worker',action='store_true');ap.add_argument('--plan');ap.add_argument('--out',required=True);ap.add_argument('--unit');ap.add_argument('--go-commit');ap.add_argument('--go-path');a=ap.parse_args()
 if a.prepare:prepare(a.out)
 else:raise SystemExit(worker(a) if a.worker else launch(a))
