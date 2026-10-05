#!/usr/bin/env python3
"""Default read-only preflight. Fresh parent GO required for one bounded cadence attempt."""
import argparse,gzip,hashlib,importlib.util,json,os,re,resource,shutil,signal,subprocess,sys,threading,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREPARED_SOURCE_COMMIT='dc1c9fbb49306480a30d552f80d3c364c173f020'
PREP='results/rtl/dsrom_cadence_admission_prepare_20261002'
BASE='results/rtl/dsrom_cadence_admission_runner_prepare_20261002'
PLAN_PATH=BASE+'/runner_plan.json';GO_PATH=BASE+'/parent_GO.json'
RUNNER_PATH='tools/run_dsrom_cadence_admission.py'
VERILATOR='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
GO_KIND='BOUNDED_D2_LAT8_IMAGE_ADMISSION_SELECTED_PAIR_ONLY'
CLAIMS_DIR=Path('/tmp/opentallas-dsrom-upstream-pair-go-claims')
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,data):
 with path.open('x') as f:
  json.dump(data,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def prep_module():
 s=importlib.util.spec_from_file_location('cadence_prepare',ROOT/'tools/prepare_dsrom_cadence_admission.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def package_sha(pins):return sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())
def reviewed_plan():
 p=json.loads((ROOT/PLAN_PATH).read_text())
 if p['prepared_source_commit']!=PREPARED_SOURCE_COMMIT:raise ValueError('prepared source commit changed')
 for path,h in p['artifact_pins'].items():
  if sha((ROOT/path).read_bytes())!=h:raise ValueError('runner preparation pin changed '+path)
 return p

def source_preflight():
 p=reviewed_plan();
 if p.get('admitted_cases')!=['existing_fast8'] or p.get('cases')!=['existing_fast8'] or p.get('compiled_LAT')!=8:raise ValueError('STALE_IMAGE_ADMISSION: runner case/LAT changed')
 source=json.loads((ROOT/PREP/'sourceplan.json').read_text());m=prep_module()
 m.OLD.JOIN.verify() # Full267-original preservation plus shared primitive/join authorities.
 # The immutable dc1c source plan binds every source input and LAT8 image.
 for path,h in source['input_source_sha256'].items():
  data=(ROOT/path).read_bytes()
  if sha(data)!=h or data!=git('show',PREPARED_SOURCE_COMMIT+':'+path):raise ValueError('source changed '+path)
 for path in ('model.json','sourceplan.json'):
  if (ROOT/PREP/path).read_bytes()!=git('show',PREPARED_SOURCE_COMMIT+':'+PREP+'/'+path):raise ValueError('prepared record changed '+path)
 files=m.package();pins={name:sha(text.encode()) for name,text in files.items()}
 if pins!=source['generated_files_sha256'] or package_sha(pins)!=p['generated_package_sha256']:raise ValueError('package changed')
 if m.expected()!=p['expected_contract']['public_oracle']:raise ValueError('oracle changed')
 return source,p

def tool_preflight(p):
 t=p['tools']
 for path,h in t['files_sha256'].items():
  if sha(Path(path).read_bytes())!=h:raise ValueError('tool file changed '+path)
 for name,path in t['resolved_commands'].items():
  if str(Path(shutil.which(name) or '/missing').resolve())!=path:raise ValueError('tool path changed '+name)
 for name,value in t['environment'].items():
  if os.environ.get(name)!=value:raise ValueError('tool environment changed '+name)
 versions={}
 vv=subprocess.run([VERILATOR,'--version'],capture_output=True,text=True,check=True,timeout=10).stdout.strip()
 if vv!=t['verilator_version']:raise ValueError('Verilator version changed')
 versions['verilator']=vv
 for name,path in t['resolved_commands'].items():
  v=subprocess.run([path,'--version'],capture_output=True,text=True,check=True,timeout=10).stdout.splitlines()[0]
  if v!=t['versions'][name]:raise ValueError('tool version changed '+name)
  versions[name]=v
 h=subprocess.run([VERILATOR,'--help'],capture_output=True,text=True,check=True,timeout=10)
 text=h.stdout+h.stderr
 if sha(text.encode())!=t['help_sha256']:raise ValueError('tool help changed')
 for token in t['help_option_tokens']:
  if token not in text:raise ValueError('option unavailable '+token)
 return dict(status='PREFLIGHT_ONLY_NO_HDL_EXECUTION',versions=versions,tool_files_sha256=t['files_sha256'],help_sha256=t['help_sha256'],compiled=False)

def host_preflight(p):
 # Read-only admission. No service creation/cgroup writes or launch-time cap fallback.
 if os.uname().nodename!=p['host_admission']['hostname']:raise RuntimeError('reviewed local host mismatch')
 manager=Path('/sys/fs/cgroup/user.slice/user-'+str(os.getuid())+'.slice/user@'+str(os.getuid())+'.service/app.slice')
 if not (manager/'cgroup.kill').exists() or not os.access(manager/'cgroup.kill',os.W_OK):raise RuntimeError('user delegated cgroup.kill not writable')
 manual=Path(p['host_admission']['systemd_service_manual'])
 if sha(manual.read_bytes())!=p['host_admission']['systemd_service_manual_sha256']:raise RuntimeError('OOMPolicy semantic manual changed')
 text=gzip.decompress(manual.read_bytes()).decode();i=text.find('OOMPolicy=')
 if i<0 or '\\fBkill\\fR' not in text[i:i+1500]:raise RuntimeError('installed OOMPolicykill semantic support unavailable')
 mem={line.split(':')[0]:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines() if line.startswith(('MemAvailable:','MemTotal:'))}
 cpus=os.cpu_count();load=list(os.getloadavg());disk=shutil.disk_usage('/tmp').free
 if mem['MemAvailable']<p['host_admission']['minimum_available_memory_bytes'] or disk<p['host_admission']['minimum_free_disk_bytes'] or load[0]>cpus-2 or not {0,1}<=set(os.sched_getaffinity(0)):raise RuntimeError('fresh local headroom insufficient')
 parent_controllers=(manager/'cgroup.controllers').read_text().strip()
 parent_subtree=(manager/'cgroup.subtree_control').read_text().strip()
 parent_cpu_max=(manager/'cpu.max').read_text().strip() if (manager/'cpu.max').exists() else None
 return dict(cpu_controllers_available=parent_controllers,cgroup_subtree_control=parent_subtree,cpu_max_observed=parent_cpu_max,CPUQuota_property_is_enforced=False,cpu_bound_policy='KERNEL_INHERITED_TASK_AFFINITY_CPUS_0_1',status='READ_ONLY_LOCAL_ADMISSION_NO_SERVICE_LAUNCHED',UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),hostname=os.uname().nodename,uid=os.getuid(),available_memory_bytes=mem['MemAvailable'],total_memory_bytes=mem['MemTotal'],free_tmp_disk_bytes=disk,CPU_count=cpus,load_1_5_15=load,delegated_parent=str(manager),delegated_cgroup_kill_writable=True,OOMPolicykill_installed_manual_sha256=p['host_admission']['systemd_service_manual_sha256'],new_execution_leaf_writable_kill_and_oom_group1='MUST_VERIFY_INSIDE_CHILD_BEFORE_COMPILE')

def verify(go_commit):
 if not isinstance(go_commit,str) or not re.fullmatch('[0-9a-f]{40}',go_commit):raise ValueError('full GO commit required')
 source,p=source_preflight();raw=git('show',go_commit+':'+GO_PATH);go=json.loads(raw)
 if go.get('GO')!=GO_KIND:raise ValueError('fresh explicit GO required')
 required={'source_prepare_commit':PREPARED_SOURCE_COMMIT,'sourceplan_sha256':sha((ROOT/PREP/'sourceplan.json').read_bytes()),'model_sha256':sha((ROOT/PREP/'model.json').read_bytes()),'bench_sha256':sha((ROOT/'rtl/test/tb_dsrom_upstream_pair_cadence_admission_prepare.sv').read_bytes()),'runner_sha256':sha((ROOT/RUNNER_PATH).read_bytes()),'runner_plan_sha256':sha((ROOT/PLAN_PATH).read_bytes()),'runner_sourceplan_sha256':sha((ROOT/BASE/'sourceplan.json').read_bytes()),'generated_package_sha256':p['generated_package_sha256'],'expected_contract_sha256':sha((ROOT/BASE/'expected_contract.json').read_bytes()),'limits':p['caps'],'cases':['existing_fast8'],'continue_control_after_negative_failure':False,'claims':p['claim_limits']}
 for key,value in required.items():
  if go.get(key)!=value:raise ValueError('GO pin/policy mismatch '+key)
 prepared=go.get('prepared_commit')
 if not isinstance(prepared,str) or not re.fullmatch('[0-9a-f]{40}',prepared):raise ValueError('full prepared runner commit required')
 if not re.fullmatch('[A-Za-z0-9_-]{8,80}',str(go.get('approval_id',''))):raise ValueError('unique approval_id required')
 for path in sorted(set([RUNNER_PATH,PLAN_PATH,*p['artifact_pins'],*source['input_source_sha256'],PREP+'/sourceplan.json'])):
  if (ROOT/path).read_bytes()!=git('show',prepared+':'+path):raise ValueError('reviewed prepared file changed '+path)
 return source,p,raw

# Qualified prior public/FIFO control checker plus strict source loader recurrence.
def completion(text,case,p,rc):
 if case!='existing_fast8':return dict(valid=False,errors=['STALE_IMAGE_ADMISSION: foreign case'])
 return prep_module().completion(text,p,rc)

def metrics(cg):
 # Optional/absent kernel interfaces are data, never a reason to lose a receipt.
 result={};errors={}
 for name in ('memory.max','memory.swap.max','memory.peak','memory.events','memory.oom.group','cpu.max','cgroup.procs','cgroup.threads'):
  try:result[name]=(cg/name).read_text().strip()
  except OSError as error:result[name]=None;errors[name]=dict(type=type(error).__name__,errno=error.errno,message=str(error))
 result['metric_read_errors']=errors
 result['CPUQuota_property_is_enforced']=False
 result['cpu_quota_proof_accepted']=False
 result['cpu_bound_policy']='KERNEL_INHERITED_TASK_AFFINITY_CPUS_0_1'
 return result

def task_affinity_audit(cg):
 result=dict(valid=True,tasks={},gone_threads=[],errors=[])
 try:
  paths=sorted(set([cg/'cgroup.threads',*cg.rglob('cgroup.threads')]))
  tids=set()
  for path in paths:
   try:tids.update(map(int,path.read_text().split()))
   except FileNotFoundError:
    if path==cg/'cgroup.threads':raise
  for tid in sorted(tids):
   try:
    affinity=sorted(os.sched_getaffinity(tid));result['tasks'][str(tid)]=affinity
    if not affinity or not set(affinity)<={0,1}:result['errors'].append('task '+str(tid)+' outside CPUs0/1: '+str(affinity))
   except ProcessLookupError:result['gone_threads'].append(tid)
  if not result['tasks']:result['errors'].append('no live cgroup task affinity observed')
 except Exception as error:result['errors'].append(repr(error))
 result['valid']=not result['errors']
 result['verification']='Every enumerated live thread, including descendants; background observations sampled0.1s. Kernel clone/exec inherit parent affinity; vanished short-lived threads are recorded, not falsely reported observed.'
 return result

def cap_receipt(cg,cpus):
 m=metrics(cg);m['cpu_affinity']=sorted(cpus)
 if m['memory.max']!='4294967296' or m['memory.swap.max']!='0' or m['memory.oom.group']!='1' or m['cpu_affinity']!=[0,1]:raise RuntimeError('exact aggregate4GiB/swap0/CPU0,1 affinity caps not applied: '+repr(m))
 if not (cg/'cgroup.kill').exists() or not os.access(cg/'cgroup.kill',os.W_OK):raise RuntimeError('whole cgroup kill unavailable')
 m['task_affinity_audit']=task_affinity_audit(cg)
 if not m['task_affinity_audit']['valid']:raise RuntimeError('actual cgroup task affinity bound failed: '+repr(m['task_affinity_audit']))
 return m

def bounded_output(proc,log,limit,kill):
 written=0
 with log.open('xb') as f:
  while True:
   block=proc.stdout.read(4096)
   if not block:break
   left=limit-written;f.write(block[:left]);written+=min(len(block),left)
   if len(block)>left:
    f.flush();kill('LOG_BYTES',dict(limit_bytes=limit,stored_bytes=written));raise RuntimeError('whole cgroup kill returned')
 return proc.wait()
def inventory(work):
 return {str(p.relative_to(work)):sha(p.read_bytes()) for p in sorted(work.rglob('*')) if p.is_file()}
def claim_GO(raw,unit):
 go=json.loads(raw);CLAIMS_DIR.mkdir(parents=True,exist_ok=True)
 write(CLAIMS_DIR/(go['approval_id']+'.json'),dict(unit=unit,GO_sha256=sha(raw),prepared_commit=go['prepared_commit'],claimed_UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())))

def capped_run(a):
 start=time.monotonic();cg=Path('/sys/fs/cgroup')/Path('/proc/self/cgroup').read_text().strip().split('::',1)[1].lstrip('/')
 a.output.mkdir(parents=True,exist_ok=False);record=dict(status='RUNNING',runs=[],used_seconds=dict(build=0.0,simulate=0.0),claims=dict(field=False,physical=False,fulltoken=False,adoption=False))
 def kill(kind,detail):
  try:write(a.output/('hard_kill_'+kind+'.json'),dict(kind=kind,detail=detail,elapsed_seconds=time.monotonic()-start,metrics=metrics(cg)))
  finally:(cg/'cgroup.kill').write_text('1')
 signal.signal(signal.SIGTERM,lambda *args:kill('WHOLE_OR_TERMINATION',{'whole_seconds':660}))
 whole=threading.Timer(max(0,660-(time.monotonic()-start)),lambda:kill('WHOLE',{'whole_seconds':660}));whole.daemon=True;whole.start()
 stop=threading.Event();monitor=None
 try:
  record['initial_metric_snapshot']=metrics(cg)
  initial=cap_receipt(cg,os.sched_getaffinity(0));write(a.output/'initial_cap_receipt.json',initial)
  source,p,raw=verify(a.go_commit)
  record.update(initial_caps=initial,GO_commit=a.go_commit,GO_sha256=sha(raw),GO=json.loads(raw),prepared_commit=json.loads(raw)['prepared_commit'],runner_commit=git('rev-parse','HEAD').decode().strip(),caps=p['caps'])
  tool=tool_preflight(p);record['tools']=tool;write(a.output/'tool_preflight.json',tool)
  resource.setrlimit(resource.RLIMIT_FSIZE,(p['caps']['per_file_hard_bytes'],)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
  affinity_log=a.output/'task_affinity_samples.jsonl';affinity_log.touch(exist_ok=False)
  record['task_affinity_sampling']=dict(interval_seconds=.1,log=affinity_log.name,inherited_kernel_bound=[0,1],quota_claim=False)
  def monitor_work():
   while not stop.wait(.1):
    try:
     audit=task_affinity_audit(cg)
     if not audit['valid']:kill('TASK_AFFINITY',audit)
     line=(json.dumps(dict(elapsed_seconds=time.monotonic()-start,audit=audit),sort_keys=True)+'\n').encode()
     if affinity_log.stat().st_size+len(line)>p['caps']['affinity_log_hard_bytes']:kill('AFFINITY_LOG',{'limit_bytes':p['caps']['affinity_log_hard_bytes']})
     with affinity_log.open('ab') as f:f.write(line)
     fs=[f for folder in (a.work,a.output) for f in folder.rglob('*') if f.is_file()];total=sum(f.stat().st_size for f in fs)
     if len(fs)>p['caps']['sampled_aggregate_files'] or total>p['caps']['sampled_aggregate_disk_bytes']:kill('SAMPLED_WORK',dict(files=len(fs),bytes=total,poll_seconds=.1,hard_aggregate_disk_quota=False))
    except FileNotFoundError:pass
  monitor=threading.Thread(target=monitor_work,daemon=True);monitor.start()
  receipt=prep_module().prepare(a.work);record['generated']=receipt;write(a.output/'preparation_receipt.json',receipt)
  if package_sha(receipt['files_sha256'])!=p['generated_package_sha256']:raise ValueError('fresh generated package changed')
  os.chdir(a.work)
  def run(case,phase,argv):
   remaining=p['caps'][phase+'_summed_seconds']-record['used_seconds'][phase]
   if remaining<=0:kill('BUDGET',dict(phase=phase,remaining_seconds=remaining))
   cap_receipt(cg,os.sched_getaffinity(0)) # Verify live tasks immediately before each launch.
   begun=time.monotonic();log=a.output/(case+'_'+phase+'.log')
   timer=threading.Timer(remaining,lambda:kill('PHASE',dict(case=case,phase=phase,remaining_seconds=remaining)));timer.daemon=True;timer.start()
   try:
    proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    # Kernel inheritance applies before exec; validate the direct child if still live.
    try:
     if not set(os.sched_getaffinity(proc.pid))<={0,1}:kill('CHILD_AFFINITY',{'pid':proc.pid})
    except ProcessLookupError:pass # Fast exits still inherit the validated parent's mask.
    rc=bounded_output(proc,log,p['caps'][phase+'_log_hard_bytes'],kill)
   finally:timer.cancel()
   elapsed=time.monotonic()-begun
   if elapsed>=remaining:kill('PHASE',dict(case=case,phase=phase,elapsed_seconds=elapsed,remaining_seconds=remaining))
   record['used_seconds'][phase]+=elapsed
   e=dict(case=case,phase=phase,argv=argv,returncode=rc,elapsed_seconds=elapsed,remaining_seconds_at_start=remaining,log_sha256=sha(log.read_bytes()),caps=cap_receipt(cg,os.sched_getaffinity(0)))
   if phase=='simulate':e['completion']=completion(log.read_text(errors='replace'),case,p,rc)
   record['runs'].append(e);write(a.output/(case+'_'+phase+'_receipt.json'),e)
   if rc or (phase=='simulate' and not e['completion']['valid']):
    failure=dict(case=case,phase=phase,receipt=case+'_'+phase+'_receipt.json',log_sha256=e['log_sha256'],diagnosis='preserve exact first failure; no expected/source changes or retry')
    if 'first_failure' not in record:
     record['first_failure']=failure;write(a.output/'first_failure.json',failure)
   return e
  build=run('shared','build',p['compile_argv'])
  if build['returncode']:record['status']='FAIL_BUILD_UNQUALIFIED'
  else:
   for case in ('existing_fast8',):run(case,'simulate',p['simulate_argv'][case])
   record['status']='PASS_BOUNDED_LAT8_ADMISSION_SELECTED_PAIR_ONLY' if all(e['completion']['valid'] for e in record['runs'][1:]) else 'FAIL_UNQUALIFIED'
 except Exception as error:
  record['status']='FAIL_RUNNER';record['exception']=repr(error);record['original_traceback']=traceback.format_exc()
 finally:
  try:
   try:record['final_metrics']=metrics(cg)
   except Exception as error:record['final_metrics_error']=repr(error) # Preserve original exception.
   try:record['artifacts_sha256']=inventory(a.work)
   except Exception as error:
    record['artifact_inventory_failure']=repr(error);record['status']='FAIL_RUNNER'
   write(a.output/'record.json',record)
  finally:stop.set();whole.cancel()
 return 0 if record['status']=='PASS_BOUNDED_LAT8_ADMISSION_SELECTED_PAIR_ONLY' else 1

def service_argv(a,unit,p):
 argv=['systemd-run','--user','--wait','--pipe','--unit='+unit]
 for v in ('MemoryMax=4294967296','MemorySwapMax=0','CPUQuota=200%','CPUAffinity=0 1','TasksMax=64','OOMPolicy=kill','RuntimeMaxSec=660s','TimeoutStopSec=1s','KillMode=control-group','KillSignal=SIGKILL'):argv+=['-p',v]
 for key,value in p['tools']['environment'].items():
  if value is not None:argv+=['--setenv='+key+'='+value]
 unset=[k for k,v in p['tools']['environment'].items() if v is None]
 if unset:argv+=['-p','UnsetEnvironment='+' '.join(unset)]
 return argv+[sys.executable,str(ROOT/RUNNER_PATH),'--execute','--capped-child','--go-commit',a.go_commit,'--output',str(a.output),'--work',str(a.work)]
def fresh_paths(output,work):
 for path in (output,work):
  if not path.is_absolute() or path.exists() or path==ROOT or ROOT in path.parents:raise ValueError('fresh external output/work required')
 if output==work or output in work.parents or work in output.parents:raise ValueError('output/work overlap')

def fresh_launcher_paths(output):
 # Only the parent owns launcher receipts; the capped child must accept them.
 for path in (Path(str(output)+'_launcher.log'),Path(str(output)+'_launcher.json'),Path(str(output)+'_host_admission.json')):
  if path.exists():raise ValueError('launcher receipt already exists')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--capped-child',action='store_true');ap.add_argument('--go-commit');ap.add_argument('--output',type=Path);ap.add_argument('--work',type=Path);a=ap.parse_args()
 if not a.execute:
  s,p=source_preflight();print(json.dumps(dict(status='PREFLIGHT_ONLY_NO_HDL_EXECUTION',source_prepare_commit=PREPARED_SOURCE_COMMIT,generated_package_sha256=p['generated_package_sha256'],tool_preflight=tool_preflight(p),host_preflight=host_preflight(p)),indent=2));return 0
 if not a.go_commit or not a.output or not a.work:ap.error('execute requires fresh GO/output/work')
 a.output=a.output.resolve();a.work=a.work.resolve();fresh_paths(a.output,a.work)
 if a.capped_child:return capped_run(a)
 fresh_launcher_paths(a.output)
 source,p,raw=verify(a.go_commit)
 if git('status','--porcelain').strip():raise RuntimeError('clean pinned worktree required')
 tool_preflight(p);host=host_preflight(p);unit='dsrom-lat8-image-admission-'+str(os.getpid());argv=service_argv(a,unit,p)
 write(Path(str(a.output)+'_host_admission.json'),host)
 claim_GO(raw,unit) # Exclusive local approval claim; never retry same approval.
 proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
# Launcher output is only service status; child logs are stored by capped child.
 rc=bounded_output(proc,Path(str(a.output)+'_launcher.log'),1048576,lambda *x:subprocess.run(['systemctl','--user','kill','--kill-whom=all','--signal=SIGKILL',unit],check=True))
 props=subprocess.run(['systemctl','--user','show',unit,'-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','MainPID','-p','ControlGroup','-p','MemoryMax','-p','MemorySwapMax','-p','MemoryPeak','-p','CPUQuotaPerSecUSec','-p','RuntimeMaxUSec','-p','KillSignal'],capture_output=True,text=True,timeout=10)
 write(Path(str(a.output)+'_launcher.json'),dict(unit=unit,argv=argv,returncode=rc,properties=props.stdout,properties_stderr=props.stderr,properties_returncode=props.returncode))
 return rc
if __name__=='__main__':sys.exit(main())
