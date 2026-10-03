from pathlib import Path
import sys,os,subprocess,time,json,hashlib,fcntl,signal,ast
ROOT=Path('/home/ubuntu/OpenTallas-hbm-bridge-f0-r3');BASE=Path('/home/ubuntu/hbm-c0-pc40-8c3dfbf79-r2-coordinator');OUT=Path('/home/ubuntu/hbm-c0-pc40-connected-8c3dfbf79-r2')
G=Path('/tmp/claude-1000/queue/fleet-admission-guard-20261002');PID=3514360
sys.path.insert(0,str(ROOT/'tools'));import h4_hbm_c0_pc40_exact_run_r2 as R
R.verify();h=R.sample()
if h['available_memory_bytes']<4*2**30:raise SystemExit('REFUSE RAM')
if __import__('shutil').disk_usage('/home/ubuntu').free<4*2**30:raise SystemExit('REFUSE disk')
# Reserve one local worker: user explicitly permits shared CPU, no fake idle.
lease=(BASE/'local_one_worker.lock').open('a+');fcntl.flock(lease,fcntl.LOCK_EX|fcntl.LOCK_NB)
with (G/'admission.lock').open('a+') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 records=list(G.glob('admitted.*.'+str(PID)+'.json'))
 threads=list((G/'thread-leases').glob('*.'+str(PID)))
 log=(BASE/'coordinator.log').read_text()
 if records or threads or 'worker ' in log or OUT.exists():raise SystemExit('REFUSE remote may already dispatch')
 cmd=Path(f'/proc/{PID}/cmdline').read_bytes()
 if b'remote_gate_guarded.py' not in cmd or b'h4_hbm_c0_pc40_exact_run_r2.py' not in cmd:raise SystemExit('REFUSE coordinator identity')
 children=Path(f'/proc/{PID}/task/{PID}/children').read_text().strip()
 # Under global acquire mutex, no new remote dispatch can race shutdown.
 os.kill(PID,signal.SIGTERM)
 for _ in range(100):
  p=Path(f'/proc/{PID}/stat')
  if not p.exists() or p.read_text().split(') ')[1][0]=='Z':break
  time.sleep(.1)
 else:raise SystemExit('REFUSE coordinator still live')
 (BASE/'remote_unlaunched_stop.json').write_text(json.dumps(dict(pid=PID,source_commit='8c3dfbf7910cb74cbc74497c787c3fc3b790bc82',under_admission_mutex=True,admitted_records=[],thread_leases=[],coordinator_log=log,children_before_stop=children,remote_dispatch=False,termination='SIGTERM acknowledged process absent/zombie',authorization='User-directed SAME request local shared CPU after proof no dispatch'),indent=2)+'\n')
# Recipe extracted from pinned runner, not an alternative HDL/source list.
tree=ast.parse((ROOT/'tools/h4_hbm_c0_pc40_exact_run_r2.py').read_text());expr=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='files' for t in n.targets))
inp=ROOT/'results/uarch/h4_hbm_c0_connected_bridge_20261003/inputs'
files=eval(compile(ast.Expression(expr),'<pinned runner files>','eval'),{'ROOT':ROOT,'inp':inp})
OUT.mkdir(exist_ok=False)
cpu=max(h['allowed_cpu_idle'],key=lambda x:x['idle_fraction'])['cpu']
r=dict(source_commit='8c3dfbf7910cb74cbc74497c787c3fc3b790bc82',status='LOCAL_SHARED_CPU_ADMITTED',headroom=h,original_dedicated_predicate_pass=h['aggregate_idle_core_equivalent']>=1,shared_CPU=True,user_authorized=True,allocated_cpu=cpu,aggregate_workers=1,nice=19,memory_reservation_bytes=4*2**30,no_process_memory_cap=True,remote_coordinator_stopped=True,HDL_gate='NOT_RUN',physical_gate=False,whole_token_gate=False,protected_upset_gate=False,scope='SAME frozen source/compile/runtime recipe; finite selected RF gate, sharedCPU host timing not hardware rate evidence',launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),source_pins=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files])
def save(): (OUT/'terminal.json').write_text(json.dumps(r,indent=2)+'\n')
save()
print(json.dumps(dict(launch_pid=os.getpid(),out=str(OUT),cpu=cpu,nice=19,status=r['status'])),flush=True)
with Path('/tmp/claude-review-20261003/codex_notes.txt').open('a') as f:f.write('\nPC40 SAME REQUEST MOVED LOCAL AFTER MUTEX-PROVEN NO REMOTE DISPATCH; coordinator3514360 stopped. Local launcherPID '+str(os.getpid())+' Nice19 CPU'+str(cpu)+' singleworker4GiBreservation (no process cap). Original >=1idle predicate FAILED and recorded; explicit user sharedCPU authorization. Out '+str(OUT)+'; launched sources unchanged8c3dfbf79. Euclidb355 address hazard not used by this bareACK controller; physical owner55 integration remains separate.\n')
def worker():os.sched_setaffinity(0,{cpu});os.nice(19)
for name,cmd in [('compile',['iverilog','-g2012','-s','tb','-o',str(OUT/'gate.vvp')]+[str(x) for x in files]),('runtime',['vvp',str(OUT/'gate.vvp')])]:
 r['status']=name.upper();r[name+'_command']=cmd;save();start=time.monotonic()
 with (OUT/(name+'.log')).open('w') as log:
  child=subprocess.Popen(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,preexec_fn=worker)
  r['live_child_pid']=child.pid;r['child_phase']=name;save();print(name+' child='+str(child.pid),flush=True);rc=child.wait()
 r[name+'_RC']=rc;r[name+'_seconds']=time.monotonic()-start;r['live_child_pid']=None;save()
 if rc:r['status']='FAIL_'+name.upper();save();raise SystemExit(rc)
text=(OUT/'runtime.log').read_text();r['HDL_gate']='PASS_CONNECTED_SELECTED_EXACT' if 'CONNECTED_PC40_PASS' in text else 'FAIL_NO_CONNECTED_TERMINAL';r['status']=r['HDL_gate'];r['binary_sha256']=hashlib.sha256((OUT/'gate.vvp').read_bytes()).hexdigest();r['source_lease_trace']=[x for x in text.splitlines() if x.startswith('EVENT ')];r['case_results']=[x for x in text.splitlines() if x.startswith('CASE_PASS ')];save();print(r['status'],flush=True)
