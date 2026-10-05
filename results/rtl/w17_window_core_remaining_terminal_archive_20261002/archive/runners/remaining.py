#!/usr/bin/env python3
"""Fresh remaining actual SUN256/QE acceptance-edge control; no healthy baseline rerun."""
import argparse,json,hashlib,subprocess,sys,os,re,time,tempfile,shutil,resource,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import importlib.util
_base_spec=importlib.util.spec_from_file_location('w17_acceptance_edge_private_fatal_policy',ROOT/'tools/w17_window_recovery_fatal_gate_run.py')
base=importlib.util.module_from_spec(_base_spec);_base_spec.loader.exec_module(base)
import w17_window_core_cancel_guard_frontend_run as profile_runner
import w17_window_core_cancel_acceptance_edge_prepare as edge
MODEL=ROOT/edge.MODEL
PROVIDER=ROOT/'results/rtl/w17_window_recovery_candidate_prepared_20261002/record.json'
PROOF=ROOT/'results/uarch/w17_window_core_cancel_join_preparation_r6_20261002/source_edge_proof.json'
PRODUCER='rtl/test/w17_window_actual_producer_cancel_declaration_repaired/ot_hdc_v41x_window_kv_blocks_cancel.sv'
TOOL=Path(__file__).resolve();STATUS='PARENT_ACTUAL_CORE_ACCEPTANCE_EDGE_REMAINING_SINGLE_GO'
CAPS={'MemoryMax':34359738368,'MemorySwapMax':0,'CPUAffinity':[30,31],'LimitFSIZE':1073741824,'LimitCORE':0,'RuntimeMaxSec':2250,'KillMode':'control-group','KillSignal':9,'OOMPolicy':'stop'}
BUDGET={'compile_shared_seconds':1950,'phase_compile_seconds':650,'frontend_phase_seconds':300,'runtime_shared_seconds':150,'short_case_seconds':10,'long_case_seconds':120,'supervision_reserve_seconds':150,'whole_seconds':2250,'aggregate_output_bytes':8589934592,'sample_interval_seconds':0.25,'compile_workers_max':2,'automatic_retries':0,'phase_count':3,'baseline_frontend_repeats':0,'baseline_CXX_repeats':0,'new_frontend_processes':3,'CXX_processes':3}
def case_seconds(args):
 return BUDGET['long_case_seconds'] if any(x in args for x in ('+CUT=SU_SUFFIX','+CUT=WC','+CUT=WS')) else BUDGET['short_case_seconds']


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
 with Path(p).open('x') as f:json.dump(v,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
def safe_sha(p):
 try:return sha(p)
 except OSError:return None

def pins():
 old,r,files=profile_runner.pins();m=json.loads(MODEL.read_text())
 if (ROOT/edge.NEW).read_text()!=edge.expected():raise ValueError('edge insertion changed old checks')
 for field in ('runtime_cone_sha256','original_source_sha256','cases','future_mutants','accounting'):
  if m[field]!=old[field]:raise ValueError('fullgeometry/source/cases/mutants/accounting changed')
 if m['bench_sha256']!=sha(ROOT/edge.NEW) or m['generator_sha256']!=sha(ROOT/'tools/w17_window_core_cancel_acceptance_edge_prepare.py'):raise ValueError('edge source/model pin')
 files.update({p:sha(ROOT/p) for p in (edge.NEW,edge.MODEL,'tools/w17_window_core_cancel_acceptance_edge_prepare.py')})
 return m,r,files


def fatal_site(marker):
 lines=(ROOT/edge.NEW).read_text().splitlines()
 hits=[n for n,line in enumerate(lines,1) if '$fatal' in line and '"'+marker+'"' in line]
 if marker=='registered go cut accepted QE':
  if len(hits)!=2 or not lines[hits[0]-2].strip().endswith('(recover || fault_pulse))'):raise ValueError('edge and original fatal sites must both remain')
 elif len(hits)!=1:raise ValueError('exact fatal source site '+marker)
 return {'basename':'tb.sv','line':hits[0],'top':'tb'}
base.fatal_site=fatal_site

def host_admission(out):
 mem={l.split(':',1)[0]:l.split(':',1)[1].strip() for l in Path('/proc/meminfo').read_text().splitlines()}
 available=int(mem['MemAvailable'].split()[0])*1024
 free=shutil.disk_usage(out).free;affinity=sorted(os.sched_getaffinity(0))
 host=socket.gethostname()
 if any(x in host.lower() for x in ('pve2','pve3')):raise ValueError('fleet drain forbids new host admission')
 if available<60129542144 or free<17179869184 or not {30,31}.issubset(affinity):raise ValueError('fresh host memory/disk/CPU admission refused')
 return {'hostname':host,'MemAvailable_bytes':available,'disk_free_bytes':free,'launcher_affinity':affinity,'minimum_available_memory_bytes':60129542144,'minimum_disk_free_bytes':17179869184,'owned_PVE2_PVE3_jobs':[]}

def build_toolchain():
 tools={}
 for name in ('make','g++','ar'):
  located=shutil.which(name)
  if located is None:raise ValueError('build tool missing '+name)
  path=Path(located).resolve()
  version=subprocess.check_output([str(path),'--version'],text=True).splitlines()[0]
  tools[name]={'path':str(path),'sha256':sha(path),'version':version}
 kit=Path(profile_runner.base.compiler()['wrapper']).parent.parent/'share/verilator/include'
 # Runtime implementation/configuration compiled or included by generated makefiles.
 files={str(x):sha(x) for x in sorted(kit.rglob('*')) if x.is_file() and x.suffix in ('.h','.cpp','.mk')}
 return {'tools':tools,'Verilator_runtime_sha256':files,'CXX_workers_max':2,'environment_override_policy':'base.compiler rejects CC/CXX/CXXFLAGS/MAKEFLAGS/MFLAGS/LD_PRELOAD and related overrides.'}

def historical_baseline():
 review=ROOT/'results/rtl/w17_window_core_full27_terminal_review_20261002/record.json'
 v=json.loads(review.read_text());run=Path(v['output']);closed=run/'baseline/phase_closed.json'
 if sha(closed)!=v['retained_file_sha256']['baseline/phase_closed.json']:raise ValueError('historical baseline closure changed')
 c=json.loads(closed.read_text())
 if c['status']!='PHASE_SEMANTIC_RECEIPTS_CLOSED' or len(c['job']['cases'])!=23:raise ValueError('historical baseline23 scope')
 for step in c['steps'][1:]:
  if step['returncode']!=0 or sha(Path(step['log']))!=step['log_sha256']:raise ValueError('historical baseline log changed')
 return {'review_record_sha256':sha(review),'closure_sha256':sha(closed),'original_bench_sha256':sha(ROOT/edge.OLD),'new_bench_inverse_insertion_sha256':hashlib.sha256((ROOT/edge.NEW).read_text().replace(edge.INSERT,'',1).encode()).hexdigest(),'runtime_cone_sha256':sha(ROOT/'rtl/test/w17_window_core_cancel_join_r8/actual_fastpp_core_selected_cone.sv'),'positive_cases':23,'reuse_scope':'Historical original-bench healthy23 receipts and identical DUT source identities only. No changed-bench binary or healthy23 execution qualification.','binary_reused':False}

def plan_object():
 m,r,files=pins();sources=[p for p in m['original_source_sha256'] if p.endswith(('.sv','.v'))]
 sources+=[m['runtime_cone_path'],PRODUCER]+[p for p in r['future_compile_inputs']['sources'] if Path(p).name!='tb.sv']
 sources=list(dict.fromkeys(sources));compiler=base.compiler();toolchain=build_toolchain()
 jobs=[]
 for label,mut in m['future_mutants'].items():
  if (label=='physical_QE_gate') != False:continue
  jobs.append({'label':label,'mutation':mut,'cases':[{'args':['+CUT='+mut['case']]+mut.get('args',[]),'expected':'FAIL','marker':mut['failure'],'fatal_receipt':fatal_site(mut['failure']),'seconds':10}]})
 for job in jobs:
  for case in job['cases']:case['seconds']=case_seconds(case['args'])
  home='{out}/'+job['label']
  job['frontend_command']=[compiler['wrapper'],'--cc','--main','--exe','--timing','--assert','--top-module','tb','-j','2','-Wno-fatal','--unroll-count','1','--unroll-limit','131072','--output-split','20000','--output-split-cfuncs','2000','-CFLAGS','-O0','-MAKEFLAGS','OPT_FAST=-O0 OPT_SLOW=-O0 OPT_GLOBAL=-O0','--Mdir',home+'/obj','-I'+home+'/sources/rtl/hdc/v41']+[home+'/sources/'+p for p in sources]+[home+'/sources/tb.sv']
  job['CXX_command']=[toolchain['tools']['make']['path'],'-C',home+'/obj','-f','Vtb.mk','-j','2','OPT_FAST=-O0','OPT_SLOW=-O0','OPT_GLOBAL=-O0']
 if len(jobs)!=3:raise ValueError('exact targeted controls required')
 dependencies={p:sha(ROOT/p) for p in ['tools/w17_window_core_cancel_guard_frontend_run.py','tools/w17_window_core_cancel_acceptance_edge_prepare.py','tools/w17_window_core_cancel_guard_reuse_phase_run.py','tools/w17_window_core_full27_terminal_review.py']}
 return {'status':'PREPARED_NOT_GO','target_local_hostname':socket.gethostname(),'runner_sha256':sha(TOOL),'model_sha256':sha(MODEL),'compiler':compiler,'build_toolchain':toolchain,'campaign':'remaining','historical_baseline':historical_baseline(),'fresh_closure_required':True,'binary_reuse':False,'dependencies_sha256':dependencies,'source_files_sha256':files,'source_inputs':sources,'jobs':jobs,'caps':CAPS,'budget':BUDGET,'source_geometry':{'SUN':256,'SUM':64,'BL':16,'IL':8,'NBMAX':192,'CHUNK8':1,'MP':1,'AW':30,'NW':21},'physical_provider':False,'runtime_qualification':False,'full_program_primary':True,'fulltoken':False,'first_failure_stops_later_phases':True}

def prepare(out):
 p=plan_object();out=Path(out);out.mkdir(parents=True,exist_ok=False);write(out/'plan.json',p)
 write(out/'parent_GO_template.json',{'status':'PENDING_NOT_AUTHORIZATION','requested_status':STATUS,'plan_sha256':sha(out/'plan.json'),'runner_sha256':sha(TOOL),'source_digest':base.digest(p['source_files_sha256']),'campaign':'remaining','historical_baseline_digest':base.digest(p['historical_baseline']),'fresh_closure_required':True,'binary_reuse':False,'dependencies_digest':base.digest(p['dependencies_sha256']),'build_toolchain_digest':base.digest(p['build_toolchain']),'jobs_digest':base.digest(p['jobs']),'caps':CAPS,'budget':BUDGET,'first_control_dependency':None,'dependency_status':'PENDING_FIRST_MEASUREMENT_AND_PARENT_REVIEW_NOT_AUTHORIZATION'})
 return p

def validate(path):
 p=json.loads(Path(path).read_text())
 if p!=plan_object():raise ValueError('plan/source/tool/geometry/command/cap changed')
 if any('--build' in j['frontend_command'] or '--binary' in j['frontend_command'] for j in p['jobs']):raise ValueError('frontend must precede CXX')
 return p

def first_dependency(g,p):
 d=g.get('first_control_dependency')
 if not isinstance(d,dict) or d.get('status')!='PARENT_REVIEWED_ACCEPTANCE_EDGE_FIRST_CONTROL_PASS':raise ValueError('reviewed first-control PASS dependency required')
 home=Path(d['output'])
 if not home.is_absolute():raise ValueError('absolute dependency output')
 for name,key in [('record.json','record_sha256'),('service_receipt.json','service_sha256'),('physical_QE_gate/phase_closed.json','closure_sha256')]:
  if sha(home/name)!=d.get(key):raise ValueError('first dependency receipt hash '+name)
 record=json.loads((home/'record.json').read_text());terminal=json.loads((home/'service_receipt.json').read_text());closed=json.loads((home/'physical_QE_gate/phase_closed.json').read_text())
 if record.get('verdict')!='PASS_ACCEPTANCE_EDGE_FIRST_CONTROL_ONLY' or record.get('campaign')!='first' or record.get('source_pins')!=p['source_files_sha256']:raise ValueError('first dependency source/scope PASS')
 if terminal.get('returncode')!=0 or any(x not in terminal.get('terminal','') for x in ('MainPID=0','Result=success','ExecMainStatus=0','ActiveState=inactive')):raise ValueError('first dependency terminal')
 if closed['job']['label']!='physical_QE_gate' or closed['job']['mutation']!=json.loads(MODEL.read_text())['future_mutants']['physical_QE_gate']:raise ValueError('first dependency exact mutation')
 c=closed['job']['cases'][0]
 if closed['status']!='PHASE_SEMANTIC_RECEIPTS_CLOSED' or len(closed['job']['cases'])!=1 or c['marker']!='registered go cut accepted QE' or c['fatal_receipt']!=fatal_site(c['marker']):raise ValueError('first dependency exact acceptance edge')
 step=closed['steps'][1]
 if sha(Path(step['log']))!=step['log_sha256']:raise ValueError('first dependency runtime log')
 base.verify_runtime(c,step['returncode'],Path(step['log']).read_text(),step['cap_events'],step['runtime_source_directory'])
 return d

def validate_GO(a,p):
 if not re.fullmatch('[0-9a-f]{40}',a.go_commit or ''):raise ValueError('fresh committed GO required')
 g=json.loads(base.git('show',a.go_commit+':'+a.go_path))
 for k,v in {'status':STATUS,'requested_status':STATUS,'plan_sha256':sha(a.plan),'runner_sha256':sha(TOOL),'source_digest':base.digest(p['source_files_sha256']),'campaign':'remaining','historical_baseline_digest':base.digest(p['historical_baseline']),'fresh_closure_required':True,'binary_reuse':False,'dependencies_digest':base.digest(p['dependencies_sha256']),'build_toolchain_digest':base.digest(p['build_toolchain']),'jobs_digest':base.digest(p['jobs']),'caps':CAPS,'budget':BUDGET}.items():
  if g.get(k)!=v:raise ValueError('GO field '+k)
 first_dependency(g,p)
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
 receipt={'verdict':('FAIL_RUNTIME_PRESERVED' if '/runtime_' in stage else 'FAIL_BUILD_PRESERVED' if stage.endswith(('/frontend','/CXX')) else 'FAIL_PREFLIGHT_OR_CLOSURE_PRESERVED'),'stage':stage,'error':repr(error),'requested_out':a.out,'receipt_out':str(out.resolve()),'plan_sha256':safe_sha(a.plan),'unit':a.unit,'GO_commit':a.go_commit,'no_retry':True,'physical_provider':False,'runtime_qualification':False}
 if not (out/'record.json').exists():write(out/'record.json',receipt)
 print('Failure receipt: '+str(out/'record.json'),file=sys.stderr)


def caps_receipt(unit):
 fields=['ControlGroup','MemoryMax','MemorySwapMax','CPUAffinity','LimitFSIZE','LimitCORE','RuntimeMaxUSec','KillMode','KillSignal','OOMPolicy']
 raw=subprocess.check_output(['systemctl','--user','show',unit]+['--property='+k for k in fields],text=True)
 got=dict(l.split('=',1) for l in raw.splitlines() if '=' in l)
 for k,v in CAPS.items():
  if k=='RuntimeMaxSec':
   if got.get('RuntimeMaxUSec') not in ('37min 30s','2250000000'):raise ValueError('actual whole cap')
  elif k=='CPUAffinity':
   if base.parse_cpu_set(got.get(k,''))!=v:raise ValueError('actual CPU cap')
  elif str(got.get(k))!=str(v):raise ValueError('actual cap '+k)
 if sorted(os.sched_getaffinity(0))!=[30,31] or resource.getrlimit(resource.RLIMIT_FSIZE)!=(1073741824,1073741824):raise ValueError('actual affinity/FSIZE')
 relative=next(l.split('::',1)[1] for l in Path('/proc/self/cgroup').read_text().splitlines() if l.startswith('0::'));cg=Path('/sys/fs/cgroup')/relative.lstrip('/')
 if got['ControlGroup']!=relative or (cg/'memory.max').read_text().strip()!=str(CAPS['MemoryMax']) or (cg/'memory.swap.max').read_text().strip()!='0':raise ValueError('actual aggregate cgroup')
 return {'systemd':got,'kernel_cgroup':str(cg),'affinity':list(os.sched_getaffinity(0))}


def stage_allowance(compile_used, phase_used, frontend):
 remaining=min(BUDGET['compile_shared_seconds']-compile_used,BUDGET['phase_compile_seconds']-phase_used)
 if frontend:remaining=min(remaining,BUDGET['frontend_phase_seconds'])
 if remaining<=0:raise ValueError('shared/phase compile budget exhausted')
 return remaining

def mutate(src,job,m):
 mut=job['mutation']
 if mut is None:return
 path=src/'tb.sv' if mut.get('target')=='bench' else src/m['runtime_cone_path']
 text=path.read_text();start=0 if mut.get('target')=='bench' else text.index('module ot_hdc_core_v41x_cancel_fastpp_enabled #(')
 if text[start:].count(mut['old'])!=1:raise ValueError('mutant not unique in selected body')
 path.write_text(text[:start]+text[start:].replace(mut['old'],mut['new']))

def worker(a):
 out=None;stage='output_ownership';p={};steps=[];compile_used=runtime_used=0;receipts=[]
 try:
  out=owned_output(a,True);stage='plan_source_validation';p=validate(a.plan);stage='GO_validation';validate_GO(a,p)
  stage='actual_caps';caps=caps_receipt(a.unit);write(out/'caps_before_compile.json',caps)
  base.BUDGET['generated_output_total_bytes']=BUDGET['aggregate_output_bytes']
  m=json.loads(MODEL.read_text())
  for job in p['jobs']:
   home=out/job['label'];src=home/'sources';src.mkdir(parents=True,exist_ok=False)
   for path,h in p['source_files_sha256'].items():
    target=src/path;target.parent.mkdir(parents=True,exist_ok=True)
    data=base.git('show',m['pin']+':'+path) if path in m['original_source_sha256'] else (ROOT/path).read_bytes()
    if hashlib.sha256(data).hexdigest()!=h:raise ValueError('snapshot pin '+path)
    target.write_bytes(data)
   shutil.copyfile(ROOT/edge.NEW,src/'tb.sv');mutate(src,job,m)
   write(home/'snapshot_sha256.json',{x.relative_to(src).as_posix():sha(x) for x in src.rglob('*') if x.is_file()})
   phase_used=0;parts=[]
   for kind in ('frontend','CXX'):
    stage=job['label']+'/'+kind
    write(home/(kind+'_started.json'),{'stage':stage,'compile_used':compile_used,'phase_used':phase_used,'monotonic_seconds':time.monotonic()})
    cmd=[x.format(out=str(out.resolve())) for x in job[kind+'_command']]
    step=base.supervised(cmd,home/(kind+'.log'),stage_allowance(compile_used,phase_used,kind=='frontend'),out)
    compile_used+=step['wall_seconds'];phase_used+=step['wall_seconds'];steps.append(step);parts.append(step)
    if step['returncode']!=0:raise ValueError(stage+' nonzero; stop no retry')
    if kind=='frontend':
     if '%Warning-UNOPTFLAT:' in (home/'frontend.log').read_text():raise ValueError('UNOPTFLAT in mutant; no runtime qualification')
     obj=home/'obj';files=base.inventory(obj)
     if 'Vtb.mk' not in files or not any(n.endswith('.cpp') for n in files) or any(n.endswith(('.o','.a','.so')) or n=='Vtb' for n in files):raise ValueError('frontend source-only closure')
     write(home/'frontend_profile.json',{'files':files,'generated_bytes':sum(v['bytes'] for v in files.values()),'step':step,'CXX_not_started':True})
   binary=home/'obj/Vtb';write(home/'binary_receipt.json',{'sha256':sha(binary),'bytes':binary.stat().st_size})
   combined=home/'compile.log'
   with combined.open('x') as f:
    for part in parts:f.write(Path(part['log']).read_text())
    f.flush();os.fsync(f.fileno())
   phase=[{'returncode':0,'wall_seconds':phase_used,'log':str(combined.resolve()),'log_sha256':sha(combined),'command':[part['command'] for part in parts]}]
   for i,case in enumerate(job['cases']):
    stage=job['label']+'/runtime_'+str(i)
    seconds=min(case['seconds'],BUDGET['runtime_shared_seconds']-runtime_used)
    if seconds<=0:raise ValueError('shared runtime budget exhausted')
    step=base.supervised([str(binary.resolve())]+case['args'],home/('runtime_'+str(i)+'.log'),seconds,out);runtime_used+=step['wall_seconds'];steps.append(step)
    step['cap_events']=base.read_clean_runtime_events(caps['kernel_cgroup']);step['runtime_source_directory']=str(src.resolve());phase.append(step)
    base.verify_runtime(case,step['returncode'],Path(step['log']).read_text(),step['cap_events'],str(src.resolve()))
   stage=job['label']+'/semantic_hash_closure'
   base.close_and_reclaim(out,home,job,phase,sha(a.plan),a.go_commit)
   receipts.append({'phase':job['label'],'frontend_CXX_seconds':phase_used,'phase_closed_sha256':sha(home/'phase_closed.json')})
  write(out/'record.json',{'verdict':'PASS_ACCEPTANCE_EDGE_REMAINING_CONTROL_ONLY','phase_receipts':receipts,'steps':steps,'compile_shared_wall_seconds':compile_used,'runtime_shared_wall_seconds':runtime_used,'sampled_output_peak_bytes':base.OUTPUT_PEAK,'GO_commit':a.go_commit,'plan_sha256':sha(a.plan),'source_pins':p['source_files_sha256'],'baseline_frontend_repeats':0,'baseline_CXX_repeats':0,'fresh_closure_required':True,'binary_reuse':False,'local_ACK_not_owner_retirement':True,'projected_deadline_not_causal_PHY':True,'causal_certificates_ever_true':False,'physical_provider':False,'runtime_qualification':True,'campaign':'remaining','first_control_dependency':json.loads(base.git('show',a.go_commit+':'+a.go_path))['first_control_dependency'],'historical_baseline':p['historical_baseline'],'changed_bench_healthy23_qualification':False,'full27_qualification':False,'fulltoken':False,'adoption':False});return 0
 except BaseException as e:
  refusal(a,out,stage,e)
  if out is not None and not (out/'progress_at_failure.json').exists():write(out/'progress_at_failure.json',{'steps':steps,'phase_receipts':receipts,'compile_shared_wall_seconds':compile_used,'runtime_shared_wall_seconds':runtime_used,'no_retry':True})
  return 1

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
  if not re.fullmatch(r'w17-recovery-resource-[A-Za-z0-9_-]+',a.unit or ''):raise ValueError('fresh resource user-unit')
  stage='fresh_host_admission';write(out/'host_admission.json',host_admission(out))
  if socket.gethostname()!=p['target_local_hostname']:raise ValueError('reviewed local hostname mismatch')
  stage='fresh_GO_claim';claim=base.claim_go(a.go_commit);write(claim/'receipt.json',{'unit':a.unit,'out':str(out.resolve()),'plan_sha256':sha(a.plan)})
  props=['MemoryMax=34359738368','MemorySwapMax=0','CPUAffinity=30 31','LimitFSIZE=1073741824','LimitCORE=0','RuntimeMaxSec=2250','KillMode=control-group','KillSignal=9','OOMPolicy=stop','Nice=10']
  command=['systemd-run','--user','--wait','--pipe','--unit='+a.unit]+['--property='+x for x in props]+['--working-directory='+str(ROOT),sys.executable,str(TOOL),'--worker','--plan',str(Path(a.plan).resolve()),'--out',str(out.resolve()),'--unit',a.unit,'--go-commit',a.go_commit,'--go-path',a.go_path]
  write(out/'launch.json',{'command':command,'plan_sha256':sha(a.plan),'GO_commit':a.go_commit,'automatic_next_stage':'Only the declared targeted phases; stop first failure; no automatic next service.'})
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
