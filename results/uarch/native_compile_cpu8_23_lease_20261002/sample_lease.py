#!/usr/bin/env python3
"""Read-only host/cgroup/affinity receipt. No service launch or mutation."""
from pathlib import Path
import datetime,hashlib,json,os,subprocess,time
OUT=Path(__file__).resolve().parent
CPUS=set(range(8,24)); HZ=os.sysconf('SC_CLK_TCK')

def read(p):
 try:return Path(p).read_text().strip()
 except (OSError,PermissionError):return None

def proc():
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   st=(p/'stat').read_text();parts=st[st.rindex(')')+2:].split()
   if parts[0]=='Z':continue
   comm=st[st.index('(')+1:st.rindex(')')]
   cg=(p/'cgroup').read_text().strip().split('::',1)[-1]
   affinities={}
   for task in (p/'task').iterdir():
    try:affinities[int(task.name)]=sorted(os.sched_getaffinity(int(task.name)))
    except ProcessLookupError:pass
   out[int(p.name)]={'comm':comm,'state':parts[0],'ppid':int(parts[1]),
      'starttime_ticks':int(parts[19]),'cpu_ticks':int(parts[11])+int(parts[12]),
      'rss_bytes':int(parts[21])*os.sysconf('SC_PAGE_SIZE'),'cgroup':cg,
      'all_task_affinities':affinities}
  except (OSError,ProcessLookupError,PermissionError,ValueError):pass
 return out

start=datetime.datetime.now(datetime.timezone.utc).isoformat();begin=time.monotonic()
a=proc();time.sleep(2);b=proc();elapsed=time.monotonic()-begin
workers=[];active_cpu_sum=0
for pid,x in b.items():
 delta=x['cpu_ticks']-a.get(pid,x)['cpu_ticks']
 if delta>0:active_cpu_sum+=delta/HZ/elapsed
 names=('vtb','vconnected','cc1','verilator','yosys','openroad','make','ninja')
 if not any(t in x['comm'].lower() for t in names):continue
 union=set().union(*(set(v) for v in x['all_task_affinities'].values()))
 x['pid']=pid;x['sampled_process_cpu_equivalents']=max(0,delta/HZ/elapsed)
 x['overlap_candidate_CPUs']=sorted(CPUS&union)
 for key in ['exe','cwd']:
  try:x[key]=os.readlink(f'/proc/{pid}/{key}')
  except OSError:x[key]=None
 workers.append(x)
mem={}
for line in Path('/proc/meminfo').read_text().splitlines():
 k,v=line.split(':',1)
 if k in ['MemTotal','MemAvailable','SwapTotal','SwapFree']:mem[k+'_bytes']=int(v.split()[0])*1024
units={}
for name in ['w17-D1-scope-parent-frontend-20261002-r2.service','hbm-qwen-connected-runtime-parent-20261002-r11-r1.service']:
 p=subprocess.run(['systemctl','--user','show',name,'--property=ActiveState,SubState,MainPID,Result,ControlGroup,MemoryCurrent,MemoryMax,MemorySwapMax,TasksCurrent,TasksMax,CPUAffinity,CPUQuotaPerSecUSec,OOMPolicy,KillMode'],capture_output=True,text=True)
 d=dict(line.split('=',1) for line in p.stdout.splitlines() if '=' in line)
 root=Path('/sys/fs/cgroup')/d.get('ControlGroup','').lstrip('/')
 d['kernel_files']={f:read(root/f) if d.get('ControlGroup') else None for f in ['memory.current','memory.max','memory.swap.max','pids.current','pids.max','cpu.max','cgroup.events']}
 d['cgroup_kill_writable']=bool(d.get('ControlGroup')) and os.access(root/'cgroup.kill',os.W_OK)
 units[name]=d
q=units['hbm-qwen-connected-runtime-parent-20261002-r11-r1.service']
qc=int(q['kernel_files']['memory.current'] or 0);qmax=32*2**30
v=os.statvfs('/tmp');disk=v.f_bavail*v.f_frsize
reserve={'owner':'parent native CXX compile proposal; Epicurus receipt only','CPUs':sorted(CPUS),
 'memory_max_bytes':64*2**30,'memory_swap_max_bytes':0,'pids_max':48,
 'build_max_seconds':900,'review_max_seconds':120,'whole_candidate_seconds':1020,
 'disk_reservation_bytes':12*2**30,'Q_reservation_bytes':qmax,'Q_CPU_reservation':[0],
 'CPU_enforcement':'inherited affinity each task verified; user cpu.max unavailable, CPUQuota property not kernel proof',
 'allocation':'proposed non-exclusive affinity lease; no unit created, no kernel limits asserted applied',
 'review_launch':'parent runner/model/source-bound GO required'}
headroom=mem['MemAvailable_bytes']-reserve['memory_max_bytes']-max(0,qmax-qc)
overlap=[x['pid'] for x in workers if x['overlap_candidate_CPUs'] and x['sampled_process_cpu_equivalents']>.01]
result={'schema':'NATIVE_COMPILE_CPU8_23_READONLY_LEASE_PROPOSAL_V1','sample_start_UTC':start,
 'sample_end_UTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'sample_seconds':elapsed,
 'host_mem':mem,'disk_available_bytes':disk,'loadavg':read('/proc/loadavg'),'CPU_count':os.cpu_count(),
 'sampled_all_process_CPU_equivalents':active_cpu_sum,'user_units':units,'workers':workers,
 'proposed_reservation':reserve,'headroom_after_64GiB_and_Q_growth_bytes':headroom,
 'disk_after_12GiB_reservation_bytes':disk-reserve['disk_reservation_bytes'],
 'memory_screen_pass':headroom>=24*2**30,'disk_screen_pass':disk>=reserve['disk_reservation_bytes'],
 'active_worker_overlap_PIDs':overlap,'exclusive_CPU_lease':False,
 'status':'HEADROOM_SCREEN_PASS_NONEXCLUSIVE_CPU_OVERLAP_REQUIRES_PARENT_COORDINATION' if headroom>=24*2**30 and disk>=reserve['disk_reservation_bytes'] else 'REFUSED_HEADROOM',
 'expiry':'snapshot only; parent must recheck immediately before launch and enforce post-launch actual cgroup/task caps',
 'owned_running_jobs':0,'new_jobs_launched':0,'existing_jobs_modified':0,
 'sampler_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
p=OUT/'receipt_r1.json'
if p.exists():raise SystemExit('receipt exists; no overwrite')
p.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:result[k] for k in ['status','sample_end_UTC','headroom_after_64GiB_and_Q_growth_bytes','disk_available_bytes','active_worker_overlap_PIDs','sampled_all_process_CPU_equivalents']},indent=2))
