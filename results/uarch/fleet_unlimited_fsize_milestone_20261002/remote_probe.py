"""Read-only host survey; no work submission, file writes, or process signals."""
from pathlib import Path
import json,os,time
mem={}
for l in Path('/proc/meminfo').read_text().splitlines():
 k,v=l.split(':',1)
 if k in ['MemTotal','MemAvailable']:mem[k]=int(v.split()[0])*1024
v=os.statvfs('/');jobs=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  s=(p/'stat').read_text();a=s[s.rindex(')')+2:].split();comm=(p/'comm').read_text().strip()
  if a[0]=='Z':continue
  if comm not in ['openroad','yosys','verilator_bin','cc1plus','cc1','g++','ld'] and not comm.startswith(('Vtb','Vconnected','Vdie','Vchip')):continue
  lim=next(x for x in (p/'limits').read_text().splitlines() if x.startswith('Max file size'))
  jobs.append({'PID':int(p.name),'comm':comm,'state':a[0],'start_ticks':int(a[19]),'threads':int(a[17]),'RSS_bytes':int(a[21])*os.sysconf('SC_PAGE_SIZE'),'FSIZE':lim,'affinity':sorted(os.sched_getaffinity(int(p.name)))})
 except (OSError,ProcessLookupError,StopIteration):pass
print(json.dumps({'observed_epoch':time.time(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mem':mem,'root_available_bytes':v.f_bavail*v.f_frsize,'loadavg':list(os.getloadavg()),'CPUs':os.cpu_count(),'jobs':jobs,'probe_process_FSIZE':next(x for x in Path('/proc/self/limits').read_text().splitlines() if x.startswith('Max file size'))}))
