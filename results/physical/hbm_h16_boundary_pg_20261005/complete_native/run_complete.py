import os,time,json,shutil,subprocess,sys,hashlib
from pathlib import Path
out=Path('/srv/opentallas-scratch2/codex/h16-boundary-pg-20261005/complete_native');out.mkdir(parents=True,exist_ok=True)
def guard(label):
 def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
 a=cpu();time.sleep(1);b=cpu();d=[v-u for u,v in zip(a,b)];idle=(d[3]+d[4])/sum(d)*os.cpu_count();load=os.getloadavg()[0]
 mem=int(next(l.split()[1] for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith('MemAvailable:')))*1024;free=shutil.disk_usage(out).free
 r=dict(load1=load,idle_cores=idle,required_CPU=16,MemAvailable_bytes=mem,admitted_RAM_GiB=16,disk_free_bytes=free,expected_retained_DB_output_bytes=4*77*1024**2)
 (out/(label+'_guard.json')).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r),flush=True)
 if load>=128 or idle<16 or mem<16*1024**3 or free<4*77*1024**2:raise SystemExit(75)
if sys.argv[-1]=='--pre':guard('pre');raise SystemExit(0)
guard('actual_exec')
base='/srv/opentallas-scratch2/codex/hbm-suattn-context-20261005/context_h16_resume'
cmd=['docker','run','--rm','-v',base+':/baseline:ro','-v','/srv/opentallas-scratch2/codex/h16-boundary-pg-20261005:/contract:ro','-v',str(out)+':/output','openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit -threads 16 /contract/verify_complete.tcl']
(out/'argv.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (out/'verify.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
(out/'terminal.exit').write_text(str(rc)+'\n');print('exit',rc)
