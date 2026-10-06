#!/usr/bin/env python3
"""One source-pinned E2 route, fresh CPU fit before/after the unchanged guard."""
import argparse, hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--density',choices=['0.55'],required=True);p.add_argument('--body-clock-sdc',type=Path);p.add_argument('--admitted',action='store_true');p.add_argument('--preflight-only',action='store_true');a=p.parse_args()
a.source=a.source.resolve();a.output=a.output.resolve()
a.output.mkdir(parents=True,exist_ok=True)
def fit(stage):
 def cpu():
  v=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));return sum(v),v[3]
 x=cpu();time.sleep(1);y=cpu();n=os.cpu_count();mem={l.split(':')[0]:int(l.split()[1])*1024 for l in Path('/proc/meminfo').read_text().splitlines()}
 row=dict(utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),stage=stage,cpus=n,load1=os.getloadavg()[0],idle_cpus=n*(y[1]-x[1])/(y[0]-x[0]),available_bytes=mem['MemAvailable'],nvme_free_bytes=shutil.disk_usage(a.output).free,threads=16,guard='/srv/opentallas-scratch/admit.sh',reservation_GiB=64)
 # No per-process cap. Disk floor is source/object inventory plus64GiB route storage.
 row['cpu_fit']=row['load1']+16<=n and row['idle_cpus']>=16
 row['fit']=row['cpu_fit'] and row['available_bytes']>=164*2**30 and row['nvme_free_bytes']>=64*2**30
 with (a.output/'headroom.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
 print(json.dumps(row),flush=True);return row['fit']
if not a.preflight_only and (not a.body_clock_sdc or not a.body_clock_sdc.is_file()):
 sys.exit('BLOCKED: divider76158 failed intrinsicSS; supply actual external fast_clk/slow_clk input-clock SDC for loaded BODY, never reroute failed source')
if not a.preflight_only:a.body_clock_sdc=a.body_clock_sdc.resolve()
if not fit('post-guard' if a.admitted else 'pre-guard'):sys.exit(75)
if a.preflight_only:sys.exit(0)
if not a.admitted:
 argv=[sys.executable,str(Path(__file__).resolve()),'--source',str(a.source),'--output',str(a.output),'--density',a.density,'--body-clock-sdc',str(a.body_clock_sdc),'--admitted']
 sys.exit(subprocess.run(['/srv/opentallas-scratch/admit.sh','64','--',*argv]).returncode)
if (a.output/'command.json').exists():sys.exit('Existing route attempt; collect/reuse it, never overwrite/relaunch')
recipe=a.source/'physical/dsrom_wfc_protected_context'
pins={x:hashlib.sha256((a.source/x).read_bytes()).hexdigest() for x in (recipe/'body_sources.f').read_text().splitlines()}
# The owner file defines the EXISTING Turing wfc_clock_ip_binding dict.
# Retain it verbatim, then install the source-pinned binder's 60/25 PLUS
# source uncertainty. Never overwrite those margins with a later 60/25.
clock_text=a.body_clock_sdc.read_text()
(a.output/'clock_owner_binding.sdc').write_text(clock_text)
pins['clock_owner_binding.sdc']=hashlib.sha256(clock_text.encode()).hexdigest()
binder=a.source/'physical/dsrom_wfc_clock_ip_boundary_20261006/clock_inputs.sdc'
pins['physical/dsrom_wfc_clock_ip_boundary_20261006/clock_inputs.sdc']=hashlib.sha256(binder.read_bytes()).hexdigest()
(a.output/'clock_inputs.sdc').write_text(
 'source /work/clock_owner_binding.sdc\n'
 'source /src/physical/dsrom_wfc_clock_ip_boundary_20261006/clock_inputs.sdc\n')
(a.output/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
variant='u'+a.density.replace('0.','')
flow='source /OpenROAD-flow-scripts/env.sh; cd /OpenROAD-flow-scripts/flow; make DESIGN_CONFIG=/src/physical/dsrom_wfc_protected_context/body_config.mk WORK_HOME=/work FLOW_VARIANT='+variant+' PLACE_DENSITY='+a.density+' NUM_CORES=16; route_rc=$?; if [ "$route_rc" -eq 0 ]; then make DESIGN_CONFIG=/src/physical/dsrom_wfc_protected_context/body_config.mk WORK_HOME=/work FLOW_VARIANT='+variant+' PLACE_DENSITY='+a.density+' NUM_CORES=16 RUN_SCRIPT=/src/physical/dsrom_wfc_protected_context/signoff.tcl RUN_LOG_NAME_STEM=protected_signoff run; exit $?; fi; exit "$route_rc"'
cmd=['docker','run','--name','zeno-wfc-'+a.output.name,'--cidfile',str(a.output/'container.id'),'-v',str(a.source)+':/src:ro','-v',str(a.output)+':/work',image,'bash','-lc',flow]
(a.output/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (a.output/'run.log').open('w') as log:rc=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT).returncode
(a.output/'terminal.exit').write_text(str(rc)+'\n')
sys.exit(rc)
