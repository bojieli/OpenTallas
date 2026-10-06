#!/usr/bin/env python3
import json,os,shutil,subprocess,time
from pathlib import Path
root=Path(__file__).resolve().parent
repair="--repair" in __import__("sys").argv
prefix="repair_" if repair else ""

def guard(label):
 def cpu():return list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:]))
 a=cpu();time.sleep(1);b=cpu();d=[y-x for x,y in zip(a,b)];idle=(d[3]+d[4])/sum(d)*os.cpu_count()
 mem=int(next(x.split()[1] for x in Path('/proc/meminfo').read_text().splitlines() if x.startswith('MemAvailable:')))*1024
 r=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),host=os.uname().nodename,load1=os.getloadavg()[0],idle_cores=idle,MemAvailable_bytes=mem,disk_free_bytes=shutil.disk_usage(root).free,estimated_peak_RAM_GiB=24,threads=16,process_memory_cap=False)
 (root/(prefix+label+'_guard.json')).write_text(json.dumps(r,indent=1)+'\n');print(r,flush=True)
 return r['load1']<128 and idle>=16 and mem>=124*1024**3 and r['disk_free_bytes']>=32*1024**3
if '--pre' in __import__('sys').argv:raise SystemExit(0 if guard('pre') else 75)
if not guard('actual_exec'):raise SystemExit(75)
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
native='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -no_init -exit /work/run.tcl && openroad -threads 16 -no_init -exit -python /work/native_probe.py'
if repair:native='source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -threads 16 -no_init -exit -python /work/native_repair.py && OT_DIAGNOSTIC_ODB=/work/real_leaf_grid_aligned.odb OT_DIAGNOSTIC_REPORT=/work/native_geometry_aligned.json openroad -threads 16 -no_init -exit -python /work/native_probe.py'
cmd=['docker','run','--rm','--name','turing-hbm-r14-real-leaf-defect-hunt'+('-repair' if repair else ''),'--cpus=16','-e','NUM_CORES=16','-v',str(root)+':/work','-w','/work',image,'bash','-lc',native]
(root/(prefix+'argv.json')).write_text(json.dumps(cmd,indent=1)+'\n')
with (root/(prefix+'native.log')).open('w') as log:rc=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
(root/(prefix+'exit')).write_text(str(rc)+'\n');guard('post');raise SystemExit(rc)
