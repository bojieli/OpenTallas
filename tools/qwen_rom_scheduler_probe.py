#!/usr/bin/env python3
"""Read-only scheduling sample of the original Qwen ROM process and PVE1.

Measures thread runtime and runnable queue wait; never changes affinity, nice,
cgroups or processes. Queue wait is observed contention, not causal attribution
of a specific peer or a prediction of gain from changing scheduling policy.
"""
import argparse
import datetime
import inspect
import json
import subprocess
from pathlib import Path


def read_sample(pid):
 import os
 root=Path('/proc')/str(pid)
 stat=root.joinpath('stat').read_text().rsplit(') ',1)[1].split()
 threads={}
 for task in root.joinpath('task').iterdir():
  try:
   tail=task.joinpath('stat').read_text().rsplit(') ',1)[1].split()
   sched=list(map(int,task.joinpath('schedstat').read_text().split()))
   status=task.joinpath('status').read_text()
   allowed=next(line.split(':',1)[1].strip() for line in status.splitlines() if line.startswith('Cpus_allowed_list:'))
   threads[task.name]=dict(start_ticks=int(tail[19]),run_ns=sched[0],wait_ns=sched[1],slices=sched[2],
    nice=int(tail[16]),processor=int(tail[36]),allowed=allowed)
  except FileNotFoundError:
   continue
 cpus={}
 for line in Path('/proc/stat').read_text().splitlines():
  fields=line.split()
  if fields and fields[0].startswith('cpu'):
   nums=list(map(int,fields[1:]));cpus[fields[0]]=dict(total=sum(nums[:8]),idle=nums[3],iowait=nums[4],steal=nums[7])
 processes={}
 for path in Path('/proc').iterdir():
  if not path.name.isdigit():continue
  try:
   tail=path.joinpath('stat').read_text().rsplit(') ',1)[1].split()
   processes[path.name]=dict(start_ticks=int(tail[19]),ticks=int(tail[11])+int(tail[12]),
    name=path.joinpath('comm').read_text().strip(),nice=int(tail[16]))
  except (FileNotFoundError,PermissionError,ProcessLookupError):continue
 cgroup=root.joinpath('cgroup').read_text().strip()
 limits={}
 if cgroup.startswith('0::'):
  folder=Path('/sys/fs/cgroup')/cgroup[3:].lstrip('/')
  while True:
   limits[str(folder)]={name:(folder/name).read_text().strip() for name in ['cpu.max','cpuset.cpus.effective'] if (folder/name).is_file()}
   if folder==Path('/sys/fs/cgroup'):break
   folder=folder.parent
 pressure={name:Path('/proc/pressure',name).read_text().strip() for name in ['cpu','memory','io']}
 return dict(start_ticks=int(stat[19]),threads=threads,cpus=cpus,processes=processes,cgroup=cgroup,
  cgroup_limits=limits,pressure=pressure,hz=os.sysconf('SC_CLK_TCK'),
  schedstats_enabled=Path('/proc/sys/kernel/sched_schedstats').read_text().strip()=='1')


def summarize(before,after,elapsed):
 if before['start_ticks']!=after['start_ticks']:raise ValueError('PID recycled')
 rows=[]
 for tid,b in before['threads'].items():
  a=after['threads'].get(tid)
  if a is None or a['start_ticks']!=b['start_ticks']:continue
  run=(a['run_ns']-b['run_ns'])/1e9;wait=(a['wait_ns']-b['wait_ns'])/1e9
  if run<0 or wait<0:raise ValueError('Scheduler counters regressed')
  rows.append(dict(tid=int(tid),run_seconds=round(run,6),runnable_wait_seconds=round(wait,6),
   cpu_percent=round(100*run/elapsed,2),wait_fraction=round(wait/(run+wait),4) if run+wait else 0,
   nice=a['nice'],affinity=a['allowed'],processor=a['processor']))
 rows.sort(key=lambda row:row['run_seconds'],reverse=True)
 host={}
 for name,b in before['cpus'].items():
  a=after['cpus'][name];dt=a['total']-b['total']
  host[name]={k+'_fraction':round((a[k]-b[k])/dt,4) if dt else None for k in ['idle','iowait','steal']}
 peers=[]
 for pid,b in before['processes'].items():
  a=after['processes'].get(pid)
  if a is None or a['start_ticks']!=b['start_ticks']:continue
  rate=100*(a['ticks']-b['ticks'])/before['hz']/elapsed
  if rate>=1:peers.append(dict(pid=int(pid),name=a['name'],cpu_percent=round(rate,2),nice=a['nice']))
 peers.sort(key=lambda row:row['cpu_percent'],reverse=True)
 dominant=rows[0] if rows else None
 wait_valid=before.get('schedstats_enabled',False) and after.get('schedstats_enabled',False)
 return dict(sample_seconds=round(elapsed,3),thread_samples=rows,host_cpu=host,top_cpu_processes=peers[:25],
  total_process_cpu_percent=round(sum(row['cpu_percent'] for row in rows),2),dominant_thread=dominant,
  runqueue_wait_counters_valid=wait_valid,
  material_runqueue_wait_observed=bool(dominant and dominant['wait_fraction']>=.10) if wait_valid else None,
  material_definition='At least 10% of dominant thread run+runqueue-wait time in this bounded sample; not wall-clock sleeping time.',
  interpretation='Per-thread runnable wait excludes synchronization sleep; affinity/nice or a named peer cannot be assigned causality from a single observational sample.',
  actions_taken=[])


def remote(binding,seconds):
 import time
 pid=1220907
 job=dict(roots=binding['roots'],scopes=['/home/ubuntu/w12/rt_tp4d'])
 identity=evaluate(binding,capture(job,binding['processes']))
 if identity['state'] not in ('live','children_live'):raise RuntimeError('Original job not live: '+identity['state'])
 expected=binding['processes'][str(pid)]['start_ticks']
 before=read_sample(pid)
 if before['start_ticks']!=expected:raise RuntimeError('Original PID start mismatch')
 start=time.monotonic();time.sleep(seconds);after=read_sample(pid);elapsed=time.monotonic()-start
 end=evaluate(binding,capture(job,binding['processes']))
 if end['state']=='identity_changed':raise RuntimeError('Original identity changed during sample')
 return dict(at=datetime.datetime.now(datetime.timezone.utc).isoformat(),identity_before=identity,identity_after=end,
  before=before,after=after,summary=summarize(before,after,elapsed))


def main():
 import w12_terminal_collect as C
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--binding',type=Path,required=True)
 ap.add_argument('--seconds',type=int,default=15,choices=range(5,31));ap.add_argument('--result',type=Path,required=True)
 a=ap.parse_args()
 if a.result.exists():ap.error('Refusing to overwrite evidence')
 binding=json.loads(a.binding.read_text())['tp4_su64_token']
 code='import datetime,json,os,socket\nfrom pathlib import Path\n'
 for fn in (C.read_process,C.capture,C.evaluate,read_sample,summarize,remote):code+=inspect.getsource(fn)+'\n'
 code+='print(json.dumps(remote('+repr(binding)+','+repr(a.seconds)+')))\n'
 proc=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',binding['endpoint'],'python3','-'],input=code,text=True,capture_output=True,timeout=50)
 if proc.returncode:raise RuntimeError(proc.stderr[-2000:])
 record=json.loads(proc.stdout);a.result.parent.mkdir(parents=True,exist_ok=True)
 with a.result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
 summary=record['summary']
 print(json.dumps({k:summary[k] for k in ['sample_seconds','total_process_cpu_percent','dominant_thread','runqueue_wait_counters_valid','material_runqueue_wait_observed']},indent=2))


if __name__=='__main__':main()
