import os,sys,subprocess,json,time,shutil,hashlib
from pathlib import Path
root=Path('/srv/opentallas-scratch2/codex/wfc-producers-20261005/map_r1');src=root/'src'
def fit(stage):
 def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]))
 a=cpu();time.sleep(2);b=cpu();m={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
 row=dict(stage=stage,utc=time.time(),load1=os.getloadavg()[0],idle_cores=(b[3]-a[3])/os.sysconf('SC_CLK_TCK')/2,mem_available_bytes=m['MemAvailable'],disk_free_bytes=shutil.disk_usage(root).free,workers=1,reservation_GiB=4,basis='full14 SRAM +4 book macro minimum source component, single-worker Yosys mapped producer context; no wholecore/array; priced logic upper30000um2 +18hardmacros, prior component1017MB allocation plus mapping margin')
 with (root/'probe_headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 return row['load1']<128 and row['idle_cores']>=1 and row['mem_available_bytes']>4*2**30 and row['disk_free_bytes']>1763342096
if len(sys.argv)==1:
 if not fit('pre-guard'):raise SystemExit(75)
 raise SystemExit(subprocess.run(['/srv/opentallas-scratch/admit.sh','4','--',sys.executable,str(Path(__file__).resolve()),'--admitted']).returncode)
if not fit('actual-exec'):raise SystemExit(75)


out=root/'loads';out.mkdir(exist_ok=False)
errors=0
for corner in ['SS','FF']:
 cmd=['docker','run','--rm','-e','WFC_CORNER='+corner,'-v',str(src)+':/src:ro','-v',str(root/'mapped')+':/input:ro','-v',str(out)+':/out','-v',str(root/'copernicus_wfc_loads.tcl')+':/probe.tcl:ro','openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29','bash','-lc','source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /probe.tcl']
 (out/(corner+'_command.json')).write_text(json.dumps(cmd,indent=2)+'\n')
 with (out/(corner+'.log')).open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
 (out/(corner+'.exit')).write_text(str(rc)+'\n');errors+=bool(rc)
(out/'terminal.exit').write_text(str(errors)+'\n')
raise SystemExit(bool(errors))
