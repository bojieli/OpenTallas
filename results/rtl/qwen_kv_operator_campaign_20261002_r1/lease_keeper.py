import fcntl,importlib.util,json,os,sys,time,subprocess
from pathlib import Path
r=Path('/tmp/claude-1000/queue/fleet-admission-guard-20261002');sys.path.insert(0,str(r));spec=importlib.util.spec_from_file_location('g',r/'remote_gate_guarded.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
host='155.103.253.226';d=Path('/tmp/h1-qwen-kv-operator-vm-20261002-r1');held=[]
with g.LOCK.open('a+')as lock:
 fcntl.flock(lock,fcntl.LOCK_EX);pool=g.load_pool();vm=pool[host];st=g.worker_status({host:vm})[host];owners=g.slot_owners(host);ram=8*sum(len(v)for v in owners.values());threads,leases=g.thread_reservations(host,owners,vm);pricing=g.price(vm,st,ram,threads,32,8);assert pricing['admit'],pricing
 for number in range(1,pricing['effective_ram_budget_gib']//8+1):
  f=open(f'{g.gate.SLOTS}/{host}.{number}','a+')
  try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(f)
  except BlockingIOError:f.close()
  if len(held)==4:break
 assert len(held)==4
 thread=(g.THREADS/(host+'.'+str(os.getpid()))).open('w+');fcntl.flock(thread,fcntl.LOCK_EX|fcntl.LOCK_NB);held.append(thread)
 rec=dict(host=host,pid=os.getpid(),threads=8,slot_gib=32,source_head='PENDING_REVIEWED_CLEAN_CAMPAIGN_GO',purpose='releasedcheckpointQwenKVoperatoronly; nofulltoken/nohardwarejob',time=time.time());thread.write(json.dumps(rec));thread.flush();os.fsync(thread.fileno())
 (d/'lease.json').write_text(json.dumps(dict(lease=rec,pricing=pricing,observed=st,prior_leases=leases,held_lock_files=[f.name for f in held],execution_admitted=False,awaits_parent_source_model_GO=True),indent=2)+'\n')
 print(json.dumps(rec),flush=True)
while not(d/'release_authorized.json').exists():
 if(d/'started.json').exists():
  unit=json.loads((d/'started.json').read_text())['unit'];p=subprocess.run(['ssh','ot-agidock128','systemctl --user show '+unit+' -p ActiveState -p MainPID'],text=True,capture_output=True);info=dict(line.split('=',1)for line in p.stdout.splitlines()if'='in line)
  if p.returncode==0 and info.get('MainPID')=='0'and info.get('ActiveState')in('inactive','failed'):
   (d/'terminal_observed.json').write_text(json.dumps(dict(observed_at=time.time(),systemd=info))+'\n');break
 time.sleep(20)
for f in held:f.close()
(d/'lease_released.json').write_text(json.dumps(dict(pid=os.getpid(),time=time.time()))+'\n')
