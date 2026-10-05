#!/usr/bin/env python3
"""Default read-only preflight. Fresh parent GO required for one bounded cadence attempt."""
import argparse,gzip,hashlib,importlib.util,json,os,re,resource,shutil,signal,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
PREPARED_SOURCE_COMMIT='6649e1759b9bdd170a8abba15cc0f70aefd15fa8'
PREP='results/rtl/dsrom_upstream_pair_cadence_prepare_20261002'
BASE='results/rtl/dsrom_upstream_pair_cadence_runner_prepare_20261002'
PLAN_PATH=BASE+'/runner_plan.json';GO_PATH=BASE+'/parent_GO.json'
RUNNER_PATH='tools/run_dsrom_upstream_pair_cadence.py'
VERILATOR='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator'
GO_KIND='BOUNDED_ACTUAL_UPSTREAM_PAIR_CADENCE_ONLY'
CLAIMS_DIR=Path('/tmp/opentallas-dsrom-upstream-pair-go-claims')
def sha(data):return hashlib.sha256(data).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)
def write(path,data):
 with path.open('x') as f:
  json.dump(data,f,indent=2,sort_keys=True);f.write('\n');f.flush();os.fsync(f.fileno())
def prep_module():
 s=importlib.util.spec_from_file_location('cadence_prepare',ROOT/'tools/prepare_dsrom_upstream_pair_cadence.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def package_sha(pins):return sha(json.dumps(pins,sort_keys=True,separators=(',',':')).encode())
def reviewed_plan():
 p=json.loads((ROOT/PLAN_PATH).read_text())
 if p['prepared_source_commit']!=PREPARED_SOURCE_COMMIT:raise ValueError('prepared source commit changed')
 for path,h in p['artifact_pins'].items():
  if sha((ROOT/path).read_bytes())!=h:raise ValueError('runner preparation pin changed '+path)
 return p

def source_preflight():
 p=reviewed_plan();source=json.loads((ROOT/PREP/'sourceplan.json').read_text());m=prep_module()
 m.JOIN.verify() # Full267-original preservation plus shared primitive/join authorities.
 # The original immutable 6649 source plan itself binds its complete source inputs.
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
 return dict(status='READ_ONLY_LOCAL_ADMISSION_NO_SERVICE_LAUNCHED',UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),hostname=os.uname().nodename,uid=os.getuid(),available_memory_bytes=mem['MemAvailable'],total_memory_bytes=mem['MemTotal'],free_tmp_disk_bytes=disk,CPU_count=cpus,load_1_5_15=load,delegated_parent=str(manager),delegated_cgroup_kill_writable=True,OOMPolicykill_installed_manual_sha256=p['host_admission']['systemd_service_manual_sha256'],new_execution_leaf_writable_kill_and_oom_group1='MUST_VERIFY_INSIDE_CHILD_BEFORE_COMPILE')

def verify(go_commit):
 if not isinstance(go_commit,str) or not re.fullmatch('[0-9a-f]{40}',go_commit):raise ValueError('full GO commit required')
 source,p=source_preflight();raw=git('show',go_commit+':'+GO_PATH);go=json.loads(raw)
 if go.get('GO')!=GO_KIND:raise ValueError('fresh explicit GO required')
 required={'source_prepare_commit':PREPARED_SOURCE_COMMIT,'sourceplan_sha256':sha((ROOT/PREP/'sourceplan.json').read_bytes()),'model_sha256':sha((ROOT/PREP/'model.json').read_bytes()),'bench_sha256':sha((ROOT/'rtl/test/tb_dsrom_upstream_pair_cadence.sv').read_bytes()),'runner_sha256':sha((ROOT/RUNNER_PATH).read_bytes()),'runner_plan_sha256':sha((ROOT/PLAN_PATH).read_bytes()),'runner_sourceplan_sha256':sha((ROOT/BASE/'sourceplan.json').read_bytes()),'generated_package_sha256':p['generated_package_sha256'],'expected_contract_sha256':sha((ROOT/BASE/'expected_contract.json').read_bytes()),'limits':p['caps'],'cases':['production5','existing_fast8'],'continue_control_after_negative_failure':True,'claims':p['claim_limits']}
 for key,value in required.items():
  if go.get(key)!=value:raise ValueError('GO pin/policy mismatch '+key)
 prepared=go.get('prepared_commit')
 if not isinstance(prepared,str) or not re.fullmatch('[0-9a-f]{40}',prepared):raise ValueError('full prepared runner commit required')
 if not re.fullmatch('[A-Za-z0-9_-]{8,80}',str(go.get('approval_id',''))):raise ValueError('unique approval_id required')
 for path in sorted(set([RUNNER_PATH,PLAN_PATH,*p['artifact_pins'],*source['input_source_sha256'],PREP+'/sourceplan.json'])):
  if (ROOT/path).read_bytes()!=git('show',prepared+':'+path):raise ValueError('reviewed prepared file changed '+path)
 return source,p,raw

# Anchored whole-line grammar: foreign/malformed/duplicate diagnostic markers fail.
PATTERNS={
 'EDGE':r'EDGE cycle=(\d+) adapt=(\d+) spine=(\d+) smpos=(\d+) smi=(\d+) have0=(\d+) have1=(\d+) sok=(\d+) adv=(\d+) cfg=(\d+) go=(\d+) xs=(\d+) u=(\d+) b=(\d+) pos=(\d+) sv=(\d+) cnt=(\d+) npush=(\d+) pop=(\d+) issue=(\d+) hazard=(\d+) gate=(\d+)',
 'EMITTED':r'EMITTED cycle=(\d+) p=(\d+) b=(\d+) pos=(\d+) q0=([0-9a-fA-F]{64}) e0=([0-9a-fA-F]{3}) q1=([0-9a-fA-F]{64}) e1=([0-9a-fA-F]{3})',
 'PUBLIC':r'PUBLIC row=(\d+) seg=(\d+) nseg=(\d+) pos=(\d+) value=([0-9a-fA-F]{8}) err=(\d+)',
 'FIRST_FAULT':r'FIRST_FAULT cycle=(\d+) pos=(\d+) cnt=(\d+) npush=(\d+) pop=(\d+) issue=(\d+) hazard=(\d+) overflow=(\d+) gate=(\d+) emitted=(\d+) pushes=(\d+) pops=(\d+) issues=(\d+) pairfault=(\d+) spinefault=(\d+)',
 'FIRST_FAULT_SOURCE':r'FIRST_FAULT_SOURCE wpos=(\d+) npos=(\d+) slot=(\d+) ca=(\d+) cd=([0-9a-fA-F]{12}) row0=([0-9a-fA-F]{4}) row1=([0-9a-fA-F]{4})',
 'REPRODUCED_FIRST_XFIFO_OVERFLOW':r'REPRODUCED_FIRST_XFIFO_OVERFLOW profile=(\d+) cycle=(\d+)',
 'PASS_EXISTING_FAST_PROFILE':r'PASS_EXISTING_FAST_PROFILE rows=(\d+) emitted=(\d+) pushes=(\d+) pops=(\d+) issues=(\d+)'}
EDGE_KEYS='cycle adapt spine smpos smi have0 have1 sok adv cfg go xs u b pos sv cnt npush pop issue hazard gate'.split()
def completion(text,case,p,rc):
 parsed={k:[] for k in PATTERNS};events=[];errors=[]
 if case not in ('production5','existing_fast8'):return dict(valid=False,errors=['foreign case'])
 fatal=bool(re.search(r'%Error|%Fatal|Assertion failed|Aborting|core dumped|Segmentation fault|\bDIFF\b|STATIC_WITNESS_NOT_REPRODUCED|FIRST_FAULT_DIFFERENT_CAUSE|CONTROL_FIRST_FAULT|PUBLIC_ORACLE_DIFFERENCE|OTHER_FAULT|UPSTREAM_ADAPTER_FAULT|CONTROL_COVERAGE|EMITTED_ORDER',text))
 for line in text.splitlines():
  key=line.split(' ',1)[0];m=re.fullmatch(PATTERNS.get(key,r'(?!)'),line)
  if m:parsed[key].append(m.groups());events.append((key,m.groups()))
  elif any(marker in line for marker in (*PATTERNS,'PASS','REPRODUCED','FIRST_FAULT')):errors.append('malformed/foreign marker '+line)
 edges=[dict(zip(EDGE_KEYS,map(int,e))) for e in parsed['EDGE']]
 if not edges or [e['cycle'] for e in edges]!=list(range(3,3+len(edges))):errors.append('missing/duplicate/out-of-order edge')
 emitted=parsed['EMITTED'];xs=[e for e in edges if e['xs']]
 if len(emitted)>16:errors.append('too many emitted slices')
 if len(emitted)!=len(xs):errors.append('emitted/edge count mismatch')
 qword=p['expected_contract']['activation_qword'];exp=p['expected_contract']['activation_e10']
 for index,(a,e) in enumerate(zip(emitted,xs)):
  cy,u,b,pos=map(int,a[:4])
  if [cy,u,b,pos]!=[e['cycle'],e['u'],e['b'],e['pos']] or [u,b,pos,e['sv']]!=[0,index%8,index//8,3] or a[4].lower()!=qword or a[6].lower()!=qword or int(a[5],16)!=exp or int(a[7],16)!=exp:errors.append('emitted order/operand mismatch')
 q=0;first_overflow=[];pushes=pops=issues=0;last_issue=-100
 for e in edges:
  if e['cnt']!=q:errors.append('FIFO recurrence mismatch cycle='+str(e['cycle']))
  if any(e[k] not in (0,1) for k in ('xs','cfg','go','npush','pop','issue','hazard','gate')):errors.append('invalid boolean')
  if e['pop']>e['issue'] or (e['issue'] and (e['cnt']==0 or e['hazard'])):errors.append('illegal issue/pop')
  if e['gate']:
   if e['issue']:
    if e['cycle']-last_issue<8:errors.append('LAT8 slot recurrence')
    last_issue=e['cycle']
   pushes+=e['npush'];pops+=e['pop'];issues+=e['issue']
   # Actual element sees root-registered go one cycle later. Before data arrival
   # this reset can only clear the already-zero queue; no go-dependent shortcut.
   q+=e['npush']-e['pop']
   if q>4:first_overflow.append(e['cycle'])
   if q<0:errors.append('FIFO underflow')
 pubs=[]
 for row,seg,nseg,pos,value,err in parsed['PUBLIC']:
  a=[int(row),int(seg),int(nseg),int(pos),int(value,16),int(err)];pubs.append(a)
  if a[:3]!=[256,0,1] or a[3] not in (0,1) or a[4:]!=[int(p['expected_contract']['public_oracle']['FP32'],16),0]:errors.append('public bits/flags/tag mismatch')
 if [a[3] for a in pubs]!=list(range(len(pubs))) or len(pubs)>2:errors.append('public order/duplicate')
 if case=='production5':
  for key in ('FIRST_FAULT','FIRST_FAULT_SOURCE','REPRODUCED_FIRST_XFIFO_OVERFLOW'):
   if len(parsed[key])!=1:errors.append('missing/duplicate '+key)
  if parsed['PASS_EXISTING_FAST_PROFILE']:errors.append('foreign control terminal')
  if len(parsed['FIRST_FAULT'])==len(parsed['FIRST_FAULT_SOURCE'])==len(parsed['REPRODUCED_FIRST_XFIFO_OVERFLOW'])==1 and edges:
   f=list(map(int,parsed['FIRST_FAULT'][0]));e=edges[-1];terminal=list(map(int,parsed['REPRODUCED_FIRST_XFIFO_OVERFLOW'][0]));src=parsed['FIRST_FAULT_SOURCE'][0]
   if f[1] not in (0,1):errors.append('fault position out of bounds')
   if f[0]!=e['cycle'] or f[2:9]!=[e['cnt'],e['npush'],e['pop'],e['issue'],e['hazard'],1,e['gate']] or f[9:13]!=[len(emitted),pushes,pops,issues] or f[13:]!=[1,0] or terminal!=[5,e['cycle']] or first_overflow!=[e['cycle']] or (e['cnt'],e['npush'],e['pop'],e['gate'])!=(4,1,0,1):errors.append('fault ownership/counters/inequality mismatch')
   if int(src[0])>1 or int(src[1])>1 or int(src[2])!=0 or int(src[3])>=25 or int(src[5],16)!=256 or int(src[6],16)!=0x8080:errors.append('fault source config/walker mismatch')
   if [k for k,v in events[-3:]]!=['FIRST_FAULT','FIRST_FAULT_SOURCE','REPRODUCED_FIRST_XFIFO_OVERFLOW']:errors.append('fault terminal order')
 else:
  if any(parsed[k] for k in ('FIRST_FAULT','FIRST_FAULT_SOURCE','REPRODUCED_FIRST_XFIFO_OVERFLOW')):errors.append('foreign fault markers')
  if parsed['PASS_EXISTING_FAST_PROFILE']!=[('2','16','16','16','16')]:errors.append('control exact terminal counts')
  if len(edges)!=p['expected_contract']['control_edge_count'] or len(emitted)!=16 or [pushes,pops,issues]!=[16,16,16] or first_overflow or q!=0 or pubs!=[[256,0,1,0,0x44000000,0],[256,0,1,1,0x44000000,0]]:errors.append('control exact events/values/counts')
  if not events or events[-1][0]!='PASS_EXISTING_FAST_PROFILE':errors.append('control terminal order')
 return dict(valid=rc==0 and not fatal and not errors,returncode=rc,fatal=fatal,errors=errors,edge_samples=len(edges),emitted_slices=len(emitted),pushes=pushes,pops=pops,issues=issues,public_rows=pubs,first_fault=parsed['FIRST_FAULT'],first_fault_source=parsed['FIRST_FAULT_SOURCE'],first_overflow_cycles=first_overflow,interpretation='actual upstream selected full-row pair diagnostic only; no field/physical/fulltoken qualification')

def metrics(cg):
 return {n:(cg/n).read_text().strip() for n in ('memory.max','memory.swap.max','memory.peak','memory.events','memory.oom.group','cpu.max','cgroup.procs')}
def cap_receipt(cg,cpus):
 m=metrics(cg);m['cpu_affinity']=sorted(cpus);quota,period=m['cpu.max'].split()
 if m['memory.max']!='4294967296' or m['memory.swap.max']!='0' or m['memory.oom.group']!='1' or m['cpu_affinity']!=[0,1] or quota=='max' or int(quota)!=2*int(period):raise RuntimeError('exact aggregate4GiB/swap0/twoCPU caps not applied')
 if not (cg/'cgroup.kill').exists() or not os.access(cg/'cgroup.kill',os.W_OK):raise RuntimeError('whole cgroup kill unavailable')
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
  initial=cap_receipt(cg,os.sched_getaffinity(0));write(a.output/'initial_cap_receipt.json',initial)
  source,p,raw=verify(a.go_commit)
  record.update(initial_caps=initial,GO_commit=a.go_commit,GO_sha256=sha(raw),GO=json.loads(raw),prepared_commit=json.loads(raw)['prepared_commit'],runner_commit=git('rev-parse','HEAD').decode().strip(),caps=p['caps'])
  tool=tool_preflight(p);record['tools']=tool;write(a.output/'tool_preflight.json',tool)
  resource.setrlimit(resource.RLIMIT_FSIZE,(p['caps']['per_file_hard_bytes'],)*2);resource.setrlimit(resource.RLIMIT_CORE,(0,0))
  def monitor_work():
   while not stop.wait(.1):
    try:
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
   begun=time.monotonic();log=a.output/(case+'_'+phase+'.log')
   timer=threading.Timer(remaining,lambda:kill('PHASE',dict(case=case,phase=phase,remaining_seconds=remaining)));timer.daemon=True;timer.start()
   try:
    proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
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
   for case in ('production5','existing_fast8'):run(case,'simulate',p['simulate_argv'][case])
   record['status']='PASS_BOUNDED_CADENCE_DIAGNOSTIC_ONLY' if all(e['completion']['valid'] for e in record['runs'][1:]) else 'FAIL_UNQUALIFIED'
 except Exception as error:record['status']='FAIL_RUNNER';record['exception']=repr(error)
 finally:
  try:
   record['final_metrics']=metrics(cg)
   try:record['artifacts_sha256']=inventory(a.work)
   except Exception as error:
    record['artifact_inventory_failure']=repr(error);record['status']='FAIL_RUNNER'
   write(a.output/'record.json',record)
  finally:stop.set();whole.cancel()
 return 0 if record['status']=='PASS_BOUNDED_CADENCE_DIAGNOSTIC_ONLY' else 1

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
 for path in (Path(str(output)+'_launcher.log'),Path(str(output)+'_launcher.json'),Path(str(output)+'_host_admission.json')):
  if path.exists():raise ValueError('launcher receipt already exists')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--execute',action='store_true');ap.add_argument('--capped-child',action='store_true');ap.add_argument('--go-commit');ap.add_argument('--output',type=Path);ap.add_argument('--work',type=Path);a=ap.parse_args()
 if not a.execute:
  s,p=source_preflight();print(json.dumps(dict(status='PREFLIGHT_ONLY_NO_HDL_EXECUTION',source_prepare_commit=PREPARED_SOURCE_COMMIT,generated_package_sha256=p['generated_package_sha256'],tool_preflight=tool_preflight(p),host_preflight=host_preflight(p)),indent=2));return 0
 if not a.go_commit or not a.output or not a.work:ap.error('execute requires fresh GO/output/work')
 a.output=a.output.resolve();a.work=a.work.resolve();fresh_paths(a.output,a.work)
 if a.capped_child:return capped_run(a)
 source,p,raw=verify(a.go_commit)
 if git('status','--porcelain').strip():raise RuntimeError('clean pinned worktree required')
 tool_preflight(p);host=host_preflight(p);unit='dsrom-upstream-pair-cadence-'+str(os.getpid());argv=service_argv(a,unit,p)
 write(Path(str(a.output)+'_host_admission.json'),host)
 claim_GO(raw,unit) # Exclusive local approval claim; never retry same approval.
 proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
# Launcher output is only service status; child logs are stored by capped child.
 rc=bounded_output(proc,Path(str(a.output)+'_launcher.log'),1048576,lambda *x:subprocess.run(['systemctl','--user','kill','--kill-whom=all','--signal=SIGKILL',unit],check=True))
 props=subprocess.run(['systemctl','--user','show',unit,'-p','Result','-p','ExecMainCode','-p','ExecMainStatus','-p','MainPID','-p','ControlGroup','-p','MemoryMax','-p','MemorySwapMax','-p','MemoryPeak','-p','CPUQuotaPerSecUSec','-p','RuntimeMaxUSec','-p','KillSignal'],capture_output=True,text=True,timeout=10)
 write(Path(str(a.output)+'_launcher.json'),dict(unit=unit,argv=argv,returncode=rc,properties=props.stdout,properties_stderr=props.stderr,properties_returncode=props.returncode))
 return rc
if __name__=='__main__':sys.exit(main())
