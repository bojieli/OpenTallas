#!/usr/bin/env python3
"""Read-only process/cgroup telemetry, separate from unchanged build commands."""
from pathlib import Path
import os,time,json,datetime
out=Path.cwd();page=os.sysconf('SC_PAGE_SIZE');pid=None;cg=None
peak_rss=peak_pss=peak_charge=0;samples=0;cg_peak=0
def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()
with (out/'aggregate_memory.jsonl').open('x',buffering=1) as log:
 log.write(json.dumps(dict(event='observer_start',UTC=stamp(),scope='Read-only1s aggregate processRSS/5sPSS and kernel cgroup charged-memory peak; no build settings/process limits'))+'\n')
 while pid is None:
  for p in Path('/proc').iterdir():
   if not p.name.isdigit():continue
   try:
    args=(p/'cmdline').read_bytes().split(b'\0')
    if len(args)>1 and Path(os.fsdecode(args[0])).name=='bash' and args[1]==b'build_fullsix.sh' and (p/'cwd').resolve()==out:
     pid=int(p.name);c=(p/'cgroup').read_text().strip().split(':',2)[2];cg=Path('/sys/fs/cgroup'+c);break
   except (OSError,IndexError):pass
  if pid is None:time.sleep(1)
 log.write(json.dumps(dict(event='build_found',UTC=stamp(),pid=pid,cgroup=str(cg)))+'\n')
 while Path('/proc',str(pid)).exists():
  try:pids=[int(p) for p in (cg/'cgroup.procs').read_text().split()]
  except OSError:pids=[pid]
  rss=0;pss=0;pss_complete=True
  for p in pids:
   try:rss+=int(Path('/proc',str(p),'statm').read_text().split()[1])*page
   except (OSError,IndexError):pass
   if samples%5==0:
    try:
     for line in Path('/proc',str(p),'smaps_rollup').read_text().splitlines():
      if line.startswith('Pss:'):pss+=int(line.split()[1])*1024
    except OSError:pss_complete=False
  try:charge=int((cg/'memory.current').read_text());cg_peak=max(cg_peak,int((cg/'memory.peak').read_text()))
  except OSError:charge=None
  peak_rss=max(peak_rss,rss);peak_pss=max(peak_pss,pss);peak_charge=max(peak_charge,charge or 0)
  log.write(json.dumps(dict(UTC=stamp(),processes=len(pids),sum_process_RSS_bytes=rss,sum_process_PSS_bytes=pss if samples%5==0 else None,PSS_complete=pss_complete if samples%5==0 else None,cgroup_current_bytes=charge,cgroup_kernel_peak_bytes=cg_peak))+'\n')
  samples+=1;time.sleep(1)
 result=dict(scope='Observed real parallel build; GNUtimechildmax is separate',samples=samples,sample_period_seconds=1,PSS_period_seconds=5,sampled_peak_sum_RSS_bytes=peak_rss,sampled_peak_sum_PSS_bytes=peak_pss,sampled_peak_cgroup_current_bytes=peak_charge,kernel_cgroup_memory_peak_bytes=cg_peak,cgroup=str(cg),limits=['RSS sums count shared pages more than once','PSS samples proportionally account shared mappings but5s samples may miss short peaks','Kernel memory.peak is charged cgroup memory including cache, not RSS','Process samples are1s snapshots, not an exact instantaneous aggregateRSS maximum'],end_UTC=stamp())
 (out/'aggregate_memory_summary.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
