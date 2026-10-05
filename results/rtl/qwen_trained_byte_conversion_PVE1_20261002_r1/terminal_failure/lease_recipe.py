import importlib.util,json,os,subprocess,time
from pathlib import Path
r=Path('/tmp/claude-1000/queue/fleet-admission-guard-20261002');import sys;sys.path.insert(0,str(r));spec=importlib.util.spec_from_file_location('guard',r/'remote_gate_guarded.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
root=Path('/home/ubuntu/OpenTallas-qwen-trained-conversion-r2');head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip();assert head=='44e58b4aaab28a3539d6d312ac80a8f8442c52dd';assert not subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True)
os.environ['OT_GATE_THREADS']='8';os.environ['OT_GUARD_SOURCE_HEAD']=head;os.environ['OT_GATE_EXCLUDE']=','.join(k for k in g.load_pool()if k!='ot-pve1')
import fcntl,math,time
host='ot-pve1';held=[]
with g.LOCK.open('a+')as lk:
 fcntl.flock(lk,fcntl.LOCK_EX)
 pool=g.load_pool();vm=pool[host];st=g.worker_status({host:vm})[host];owners=g.slot_owners(host);ram=8*sum(len(v)for v in owners.values());threads,leases=g.thread_reservations(host,owners,vm)
 pricing=g.price(vm,st,ram,threads,80,8)
 assert set(pricing['reasons'])<={'AGGREGATE_THREADS'},pricing
 assert threads==28 and st['compute_threads']==28, (threads,st)
 assert len(leases)==1 and leases[0]['pid']==2491424,leases
 for k in range(1,pricing['effective_ram_budget_gib']//8+1):
  f=open(f'{g.gate.SLOTS}/{host}.{k}','a+')
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(f)
  except BlockingIOError:f.close()
  if len(held)==10:break
 assert len(held)==10
 import hashlib
 wt=open(f'{g.gate.SLOTS}/{host}.wt.{hashlib.md5(str(root).encode()).hexdigest()[:12]}','a+');fcntl.flock(wt,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(wt)
 tf=(g.THREADS/(host+'.'+str(os.getpid()))).open('w+');fcntl.flock(tf,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(tf)
 rec=dict(host=host,pid=os.getpid(),threads=8,slot_gib=80,cwd=str(root),time=time.time(),source_head=head,CPU_sharing=True,authorization='Parent explicitly directs sole PVE1 conversion after disclosed protected28worker W11 demand; memory/disk remain capacity-priced; no global guard modification.')
 tf.write(json.dumps(rec));tf.flush();os.fsync(tf.fileno())
 (Path('/tmp/h1-trained-byte-conversion-pve1-20261002')/'shared_CPU_admission.json').write_text(json.dumps(dict(lease=rec,pricing=pricing,observed=st,existing_leases=leases,CPU_model=dict(physical_CPUs=28,protected_configured_workers=28,conversion_workers=8,configured_peak_ratio=36/28,conservative_guard_doublecount_workers=64,observed_load=st['load'],exclusive_CPUs=False,Nice=10,wall_deadline=None,performance_credit=False),authorized_peak_thread_exception_only=True),indent=2)+'\n')
d=Path('/tmp/h1-trained-byte-conversion-pve1-20261002');receipt=dict(host=host,source_commit=head,lease_keeper_pid=os.getpid(),memory_reservation_GiB=80,threads=8,CPU_sharing=True,Nice=10,admission='Parent-directed CPU sharing; exact memory/disk reservations remain enforced',held_lock_files=[f.name for f in held],source_model='18ff7ccc5',capacity_basis='PVE1 fresh199GiB available; existing finite row-stream source model, retain80GiB fleet-capacity reservation, no smaller guessed process cap. This is fleet capacity protection, not an estimated workload peak.',no_wall_cap=True,no_FSIZE_cap=True,no_AS_cap=True)
(d/'lease.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt),flush=True)
# Hold through setup/conversion. Release only on explicit completed marker or actual service terminal after started marker.
while True:
 if(d/'lease_release_authorized.json').exists():break
 if(d/'conversion_started.json').exists():
  p=subprocess.run(['ssh','ot-pve1','systemctl --user show hbm-qwen-trained-byte-conversion-pve1-20261002-r1.service --property=ActiveState,MainPID'],text=True,capture_output=True)
  info=dict(x.split('=',1)for x in p.stdout.splitlines()if'='in x)
  if p.returncode==0 and info.get('MainPID')=='0' and info.get('ActiveState')in ('inactive','failed'):
   (d/'conversion_service_terminal.json').write_text(json.dumps(dict(observed_at=time.time(),systemd=info))+'\n');break
 time.sleep(30)
for f in held:f.close()
(d/'lease_released.json').write_text(json.dumps(dict(time=time.time(),keeper_pid=os.getpid()))+'\n')
