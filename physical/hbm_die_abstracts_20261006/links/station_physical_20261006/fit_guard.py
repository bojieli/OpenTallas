#!/usr/bin/env python3
# One attempt; no RAM-only queued waiter. The shared guard is unchanged.
import argparse,os,time,json,subprocess,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--receipt',required=True);p.add_argument('--post',action='store_true');p.add_argument('--need-gib',type=float,default=8);p.add_argument('cmd',nargs=argparse.REMAINDER);a=p.parse_args()
assert 0<a.need_gib<=8, 'actual currently usable AGI declaration <=8GiB required'
guard=Path('/srv/opentallas-scratch/admit.sh');core=guard.with_name('admit_core.py')
def stat():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
x=stat();time.sleep(1);y=stat();d=[b-c for c,b in zip(x,y)];ncpu=os.cpu_count();idle=d[3]/sum(d)*ncpu
m={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('MemTotal:','MemAvailable:'))}
reserve=min(100*2**30,int(.15*m['MemTotal']));recent=json.loads(guard.with_name('admit.recent.json').read_text());ramp=sum(v for t,v in recent if time.time()-t<180)
v=os.statvfs('/srv/opentallas-scratch');free=v.f_bavail*v.f_frsize
r={'UTC':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'phase':'post' if a.post else 'pre','cpu_count':ncpu,'load1':os.getloadavg()[0],'idle_cpu_equivalents':idle,'threads':16,'need_GiB':a.need_gib,'available_GiB':m['MemAvailable']/2**30,'reserve_GiB':reserve/2**30,'recent_peak_GiB':ramp/2**30,'disk_free_GiB':free/2**30,'disk_need_GiB':8,'guard_sha256':hashlib.sha256(guard.read_bytes()).hexdigest(),'guard_core_sha256':hashlib.sha256(core.read_bytes()).hexdigest()}
r['cpu_fit']=r['load1']+16<=ncpu and idle>=16
# Post-admission recent includes this job's declared need; do not double count.
r['memory_fit']=m['MemAvailable']>=reserve+(0 if a.post else ramp)+a.need_gib*2**30
r['disk_fit']=free>=8*2**30
with open(a.receipt,'a') as f:f.write(json.dumps(r)+'\n')
if not(r['cpu_fit'] and r['memory_fit'] and r['disk_fit']):print('CAPACITY_HOLD',json.dumps(r));raise SystemExit(75)
cmd=a.cmd[1:] if a.cmd[:1]==['--'] else a.cmd
if a.post:os.execvp(cmd[0],cmd)
os.execv(str(guard),[str(guard),str(a.need_gib),'--','python3',str(Path(__file__).resolve()),'--post','--need-gib',str(a.need_gib),'--receipt',a.receipt,'--',*cmd])
