#!/usr/bin/env python3
"""Fresh E1 CPU/RAM/NVMe fit around the existing unchanged admission guard."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

p = argparse.ArgumentParser()
p.add_argument('--receipt', type=Path, required=True)
p.add_argument('--post', action='store_true')
p.add_argument('cmd', nargs=argparse.REMAINDER)
a = p.parse_args()
guard = Path('/srv/opentallas-scratch/admit.sh')

def cpu():
    return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))

x=cpu();time.sleep(1);y=cpu();d=[b-c for c,b in zip(x,y)]
ncpu=os.cpu_count();idle=d[3]/sum(d)*ncpu
m={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()
   if l.startswith(('MemTotal:','MemAvailable:'))}
recent=json.loads(guard.with_name('admit.recent.json').read_text())
ramp=sum(v for t,v in recent if time.time()-t<180)*2**30
reserve=min(100*2**30,int(.15*m['MemTotal']))
v=os.statvfs('/srv/opentallas-scratch');free=v.f_bavail*v.f_frsize
r=dict(UTC=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()), phase='post' if a.post else 'pre',
       cpu_count=ncpu,load1=os.getloadavg()[0],idle_cpu_equivalents=idle, threads=16,
       need_GiB=16, available_bytes=m['MemAvailable'],reserve_bytes=reserve,
       recent_peak_bytes=ramp,disk_free_bytes=free,disk_need_GiB=16,
       guard_sha256=hashlib.sha256(guard.read_bytes()).hexdigest(),
       guard_core_sha256=hashlib.sha256(guard.with_name('admit_core.py').read_bytes()).hexdigest())
r['cpu_fit']=r['load1']+16<=ncpu and idle>=16
r['memory_fit']=m['MemAvailable']>=reserve+(0 if a.post else ramp)+16*2**30
r['disk_fit']=free>=16*2**30
with a.receipt.open('a') as f:f.write(json.dumps(r)+'\n')
if not(r['cpu_fit'] and r['memory_fit'] and r['disk_fit']):
    print('CAPACITY_HOLD',json.dumps(r));raise SystemExit(75)
cmd=a.cmd[1:] if a.cmd[:1]==['--'] else a.cmd
if a.post:os.execvp(cmd[0],cmd)
os.execv(str(guard),[str(guard),'16','--','python3',str(Path(__file__).resolve()),
          '--post','--receipt',str(a.receipt),'--',*cmd])
