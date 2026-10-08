import json,os,subprocess,sys,time,shutil
from pathlib import Path
root=Path('/srv/opentallas-scratch2/codex/fspine-v9-cfg-provider-20261005')
src=root/'src_synth_r2';out=root/'linked_input_r3'
def fit(stage):
    def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
    a=cpu();time.sleep(2);b=cpu()
    mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
    row=dict(utc=time.time(),stage=stage,load1=os.getloadavg()[0],idle_cores=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/2,mem_available_bytes=mem['MemAvailable'],disk_free_bytes=shutil.disk_usage(root).free,workers=1,reservation_GiB=1)
    with (root/'probe_r3_headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    return row['load1']<128 and row['idle_cores']>=1 and row['mem_available_bytes']>2**30 and row['disk_free_bytes']>1763342096
if len(sys.argv)==1:
    if not fit('pre-guard'):raise SystemExit(75)
    raise SystemExit(subprocess.run(['/srv/opentallas-scratch/admit.sh','1','--',sys.executable,str(Path(__file__).resolve()),'--admitted']).returncode)
if not fit('actual-exec'):raise SystemExit(75)
out=root/'receiver_probe_r3'
out.mkdir(exist_ok=False)
for corner in ('SS','FF'):
 cmd=['docker','run','--rm','-v',str(src)+':/src:ro','-v',str(root/'linked_input_r3')+':/input:ro','-v',str(out)+':/out','-v',str(root/'cfg_loads.tcl')+':/probe.tcl:ro','-e','CFG_CORNER='+corner,'openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 1 -exit /probe.tcl']
 with (out/(corner+'.log')).open('w') as f:rc=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT).returncode
 (out/(corner+'.exit')).write_text(str(rc)+'\n')
 if rc:raise SystemExit(rc)
