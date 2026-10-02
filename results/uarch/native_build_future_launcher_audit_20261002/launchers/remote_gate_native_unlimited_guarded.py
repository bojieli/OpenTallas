#!/usr/bin/env python3
"""Opt-in future-job gate. Live legacy dispatchers are not modified or signalled."""
import sys
import fcntl,hashlib,importlib.util,json,math,os,re,subprocess,tempfile,time
from pathlib import Path
sys.path.insert(0,'/tmp/claude-1000/queue/fleet-admission-guard-20261002')
from admission_policy import price
SOURCE_R=Path(__file__).resolve().parent
R=Path('/tmp/claude-1000/queue/fleet-admission-guard-20261002')
spec=importlib.util.spec_from_file_location('legacy_gate',SOURCE_R/'remote_gate_native_unlimited.base.py');gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
REAL_LOAD=gate.load_pool
LOCK=R/'admission.lock';THREADS=R/'thread-leases';THREADS.mkdir(exist_ok=True)
def atomic(path,data):
 fd,n=tempfile.mkstemp(dir=path.parent,prefix=path.name+'.')
 with os.fdopen(fd,'w') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(n,path)
def load_pool():
 live=REAL_LOAD();over=json.loads((R/'pool.proposed.json').read_text())
 for h,v in live.items():
  if h in over:
   for k in ['ram_gb','physical_ram_gb','reserved_headroom_gib','max_aggregate_threads','max_single_request_gib']:
    if k in over[h]:v[k]=over[h][k]
 return live
PROBE=r'''
import json,os,time
from pathlib import Path
mem={x.split(':')[0]:int(x.split()[1])/1048576 for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith(('MemTotal:','MemAvailable:'))}
workers=0
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  comm=(p/'comm').read_text().strip();args=[x.decode(errors='replace') for x in (p/'cmdline').read_bytes().split(b'\0') if x]
  s=(p/'stat').read_text();v=s[s.rindex(')')+2:].split()
  if v[0]=='Z':continue
  if comm in ['cc1plus','cc1','ld','ld.lld','collect2']:workers+=1
  elif comm in ['openroad','verilator_bin']:
   peak=1
   for i,a in enumerate(args[:-1]):
    if a in ['-threads','-j','--threads']:
     try:peak=max(peak,int(args[i+1]))
     except ValueError:pass
   workers+=peak
  elif comm.startswith(('Vtb','Vdie','Vchip','qwen','v41_')):workers+=max(1,int(v[17]))
 except OSError:continue
print(json.dumps(dict(observed_at=time.time(),total_gib=mem['MemTotal'],free_gib=mem['MemAvailable'],load=os.getloadavg()[0],cpus=os.cpu_count(),compute_threads=workers)))
'''
def worker_status(pool):
 out={}
 for h,v in pool.items():
  if v.get('disabled') or v.get('admission_hold_owner')=='user':continue
  try:
   result=subprocess.run(gate.SSH+['ubuntu@'+h,'python3 -'],input=PROBE,capture_output=True,text=True,timeout=25,check=True)
   out[h]=json.loads(result.stdout)
  except (subprocess.SubprocessError,ValueError):continue
 return out

def slot_owners(host):
 # Read kernel flock owners; do not disturb live reservations. All numeric slots count,
 # including old slot numbers outside a reduced future budget.
 locks=Path('/proc/locks').read_text().splitlines();owned={}
 for p in Path(gate.SLOTS).glob(host+'.*'):
  if not p.name[len(host)+1:].isdigit():continue
  s=p.stat();key=f'{os.major(s.st_dev):02x}:{os.minor(s.st_dev):02x}:{s.st_ino}'
  for row in locks:
   a=row.split()
   if len(a)>5 and a[5]==key:owned.setdefault(int(a[4]),[]).append(p.name)
 return owned

def thread_reservations(host,owners,vm):
 total=0;guarded=set();metadata=[]
 for p in THREADS.glob(host+'.*'):
  with p.open('a+') as f:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);continue
   except BlockingIOError:pass
   try:d=json.loads(p.read_text());total+=d['threads'];guarded.add(d['pid']);metadata.append(d)
   except (ValueError,KeyError):return vm['max_aggregate_threads'],[dict(reason='UNREADABLE_THREAD_LEASE')]
 evidence=json.loads((R/'legacy-thread-reservations.json').read_text())
 for pid in owners:
  if pid in guarded:continue
  try:
   s=Path('/proc/'+str(pid)+'/stat').read_text();start=int(s[s.rindex(')')+2:].split()[19])
  except OSError:continue
  matched=[x for x in evidence if x['host']==host and x['pid']==pid and x['start_ticks']==start]
  # Unknown legacy peaks reserve the entire host thread budget until independently priced.
  n=matched[0]['threads'] if matched else vm['max_aggregate_threads']
  total+=n;metadata.append(dict(pid=pid,start_ticks=start,threads=n,kind='legacy',known=bool(matched)))
 return total,metadata

def acquire(min_gb,cwd):
 threads=int(os.environ['OT_GATE_THREADS']);need=math.ceil(min_gb/8)
 while True:
  with LOCK.open('a+') as lk:
   fcntl.flock(lk,fcntl.LOCK_EX)
   pool=load_pool();st=worker_status(pool);decisions={}
   for host,vm in sorted(pool.items()):
    if vm.get('disabled') or vm.get('admission_hold_owner')=='user' or host in os.environ.get('OT_GATE_EXCLUDE','').split(','):continue
    owners=slot_owners(host);ram=8*sum(len(a) for a in owners.values());cpu,leases=thread_reservations(host,owners,vm)
    decision=price(vm,st.get(host,{}),ram,cpu,min_gb,threads);decision['existing_thread_leases']=leases;decisions[host]=decision
    if not decision['admit']:continue
    held=[]
    try:
     for k in range(1,int(decision['effective_ram_budget_gib'])//8+1):
      f=open(f'{gate.SLOTS}/{host}.{k}','a+')
      try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(f)
      except BlockingIOError:f.close()
      if len(held)==need:break
     if len(held)!=need:continue
     wt=open(f'{gate.SLOTS}/{host}.wt.{hashlib.md5(cwd.encode()).hexdigest()[:12]}','a+')
     try:fcntl.flock(wt,fcntl.LOCK_EX|fcntl.LOCK_NB)
     except BlockingIOError:wt.close();continue
     held.append(wt)
     p=THREADS/(host+'.'+str(os.getpid()));tf=p.open('w+');fcntl.flock(tf,fcntl.LOCK_EX);held.append(tf)
     rec=dict(host=host,pid=os.getpid(),threads=threads,slot_gib=need*8,cwd=cwd,time=time.time(),source_head=os.environ['OT_GUARD_SOURCE_HEAD'])
     tf.write(json.dumps(rec));tf.flush();os.fsync(tf.fileno())
     atomic(R/('admitted.'+host+'.'+str(os.getpid())+'.json'),dict(lease=rec,pricing=decision))
     atomic(R/'latest-pricing.json',decisions)
     # descriptors returned to legacy lifecycle; every existing close releases RAM + thread leases.
     done=held;held=[];return host,done
    finally:
     for f in held:f.close()
   atomic(R/'latest-pricing.json',decisions)
  time.sleep(20)

def main():
 if not os.environ.get('OT_GATE_THREADS'):raise SystemExit('OT_GATE_THREADS must declare the pinned job maximum aggregate worker threads')
 if os.environ.get('OT_ALLOW_LOCAL')=='1':raise SystemExit('Guarded remote variant requires local work to use its separately coordinated local gate')
 root=Path.cwd();head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
 dirty=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],text=True)
 if dirty:raise SystemExit('Guarded jobs require a pinned clean worktree')
 if str(root)=='/home/ubuntu/OpenTallas':raise SystemExit('Long jobs must use a pinned clean worktree, not main checkout')
 plan=json.loads(Path(os.environ['OT_GUARD_JOB_MANIFEST']).read_text())
 sys.path.insert(0,str(root/'tools'))
 from native_build_completion_policy_r2 import validate_model,validate_native_argv
 validate_model(plan)
 validate_native_argv(os.sys.argv[1:])
 if plan['memory_bytes'] != plan['memory_gib'] * (1<<30) or plan['workers'] != plan['threads']:
  raise SystemExit('Native capacity fields must match shared fleet reservation')
 if plan.get('source_head')!=head or plan.get('threads')!=int(os.environ['OT_GATE_THREADS']) or plan.get('memory_gib')!=int(os.environ.get('OT_GATE_MIN_GB','20')) or plan.get('model_ready') is not True or plan.get('thread_limits_priced') is not True:
  raise SystemExit('Pinned job manifest must match source, memory, thread peak and model-ready admission')
 if plan.get('file_size_policy')!='unlimited':raise SystemExit('Future job manifest must bind unlimited file-size policy')
 for required in ['tools/native_build_unlimited_exec.py','tools/native_build_completion_policy_r2.py','tools/experiment_unlimited_fsize_policy.py']:
  if required not in plan.get('source_pins',{}):raise SystemExit('Future child entry/policy must be source-pinned')
 if plan.get('command')!=os.sys.argv[1:] or not plan.get('source_pins'):raise SystemExit('Manifest must pin the exact command and its resource-limiting launcher sources')
 for name,digest in plan['source_pins'].items():
  if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:raise SystemExit('Job recipe pin mismatch: '+name)
 os.environ['OT_GUARD_SOURCE_HEAD']=head
 gate.load_pool=load_pool;gate.worker_status=worker_status;gate.acquire=acquire
 return gate.main()
if __name__=='__main__':raise SystemExit(main())
