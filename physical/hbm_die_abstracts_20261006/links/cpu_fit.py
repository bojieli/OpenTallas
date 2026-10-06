#!/usr/bin/env python3
"""One fresh CPU-fit attempt before AND after the unchanged host RAM guard.

Exit75 means capacity hold, not an admitted job. No RAM-only queued waiter,
reservation edits, process caps, migration, cancellation or capacity overrides.
Kant coordinates a retry at the next free CPU slot. --need-gib must come from
actual inventory/measurement supplied by the caller; it has no guessed default.
"""
import argparse,json,os,subprocess,time
from pathlib import Path
GUARD='/srv/opentallas-scratch/admit.sh'
def sample():
 return [int(x) for x in Path('/proc/stat').read_text().splitlines()[0].split()[1:]]
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--threads',type=int,default=16);p.add_argument('--need-gib',type=float,required=True)
 p.add_argument('--disk-need-gib',type=float,required=True);p.add_argument('--receipt',type=Path,required=True);p.add_argument('--post',action='store_true')
 p.add_argument('command',nargs=argparse.REMAINDER);a=p.parse_args()
 if not Path(GUARD).is_file() or not Path('/srv/opentallas-scratch2').is_dir():p.error('EPYC2 guard and NVMe2 required')
 if not 16<=a.threads<=24:p.error('owner thread budget16-24')
 c=sample();time.sleep(1);d=sample();delta=[y-x for x,y in zip(c,d)]
 ncpu=os.cpu_count();idle=delta[3]/sum(delta[:8])*ncpu
 load=os.getloadavg()[0];disk=os.statvfs('/srv/opentallas-scratch2')
 rec=dict(time=time.time(),phase='post' if a.post else 'pre',cpu_count=ncpu,load1=load,idle_cpu_equivalents=idle,threads=a.threads,need_gib=a.need_gib,disk_free_gib=disk.f_bavail*disk.f_frsize/2**30)
 rec['cpu_fit']=load+a.threads<=ncpu and idle>=a.threads
 rec['disk_fit']=rec['disk_free_gib']>=a.disk_need_gib
 a.receipt.parent.mkdir(parents=True,exist_ok=True)
 with a.receipt.open('a') as f:f.write(json.dumps(rec)+'\n')
 if not rec['cpu_fit'] or not rec['disk_fit']:print('CPU_CAPACITY_HOLD');return 75
 cmd=a.command[1:] if a.command[:1]==['--'] else a.command
 if not cmd:p.error('command required')
 if a.post:os.execvp(cmd[0],cmd)
 os.execv(GUARD,[GUARD,str(a.need_gib),'--','python3',str(Path(__file__).resolve()),'--post','--threads',str(a.threads),'--need-gib',str(a.need_gib),'--disk-need-gib',str(a.disk_need_gib),'--receipt',str(a.receipt.resolve()),'--',*cmd])
if __name__=='__main__':raise SystemExit(main())
