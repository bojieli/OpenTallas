#!/usr/bin/env python3
"""Source-pinned PVM placement-only diagnostic. Never a gate receipt or CTS run."""
import hashlib,json,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/ref_tile'))
import pre_route_gate as G

def main():
 kd=ROOT/'physical/ref_tile/smh_pvm_ref_s3';spec=json.loads((kd/'spec.json').read_text());fp=json.loads((kd/'floorplan.json').read_text())
 ref=set(fp['referenced']);ref|=G.referenced_closure(sorted(ref))[0]
 missing=G.absent_working_inputs(ref)
 if missing:raise RuntimeError(missing)
 dirs={'tools','rtl',str(kd.relative_to(ROOT)),'physical/qwen_die_masters','physical/common_flow','physical/hbm_accel_die_views/stations/bench','physical/hbm_w2_rb_station_20261006'}|{str(Path(p).parent) for p in ref}
 plan,payloads=G.HO.capture_plan(G.DAEMON_TREE,ROOT)
 data=G.ship_tar(dirs,payloads,{f['path']:f['mode'] for f in plan['files']})
 budget=G.gate_disk_budget(spec,data,20)
 picked=subprocess.run(['ot-run','--mem','32','--threads','16','--disk',str(budget['pick_gb']),'--dir','/srv/opentallas-scratch','--pick'],check=True,text=True,capture_output=True)
 print(picked.stderr,flush=True);host=picked.stdout.strip()
 ts=time.strftime('%Y%m%d-%H%M%S');r='/srv/opentallas-scratch/claude/codex-pvm-place-'+ts
 binding=G.SB.snapshot(data,ROOT,G.SB.git_head(ROOT),G.DAEMON_TREE,G.SB.git_head(G.DAEMON_TREE),G.SHIP_HELPERS)
 binding.update(remote_host=host,remote_run=r,route_overlay_plan=plan,disk_admission=budget,diagnostic_only=True,CTS=False,TRIAL=False)
 script=G.REMOTE_SH.format(R=r,COMMIT=binding['commit'],CAP=2700,KIT=kd.relative_to(ROOT),IMG='openroad/orfs:latest',RC=','.join(G.GATE_REFUSE),TBX=G.textbook_reset_args(spec)+G.reset_landing_args(spec),BRP='',TOP=spec['top'],CTS=0,TRIAL=0,GRTX='',CLKS=','.join(G.RT.declared_clock_ports(spec)),CLK=spec['clock_port'],ARCHIVE_SHA256=binding['archive_sha256'],STEP_CAP=G.GATE_STEP_CAP_S,PGM=G.PF.ROUTE_PIN_GROUP_MAX)
 script=G.gate_route_clock_hooks(script,spec);script=G.gate_route_hold_context(script,spec,str(kd.relative_to(ROOT)))
 script+="""
# Placement-only continuation. No cts, grt, or physical-qualification receipt.
set -e
[ -f "$C/config.mk" ]
docker run --rm -v "$R/src:/src:ro" -v "$C:/work" -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base place" > "$R/place.log" 2>&1
printf 'PVM_PLACEMENT_RC=0\n'
find "$C/results" -name '3_*odb' -printf '%p\n'
# The exact pre-DPL hook validates actual macro/fence/register coordinates before legalization.
grep 'PVM_HOP' "$C"/logs/asap7/*/base/*place*.log
printf 'PVM_CHARACTERIZATION_TERMINAL=PASS_NO_CTS\n'
"""
 binding['remote_script_sha256']=hashlib.sha256(script.encode()).hexdigest()
 out=Path('/home/ubuntu/artifacts/codex-pvm-safe2/placement_'+ts);out.mkdir(parents=True)
 (out/'source_snapshot.json').write_text(json.dumps(binding,indent=2)+'\n');(out/'run.sh').write_text(script)
 subprocess.run(['ssh',host,'mkdir -p '+r],check=True)
 subprocess.run(['ssh',host,'cat > '+r+'.tgz'],input=data,check=True)
 subprocess.run(['ssh',host,'cat > '+r+'/run.sh'],input=script.encode(),check=True)
 subprocess.run(['ssh',host,'cat > '+r+'/source_snapshot.json'],input=(out/'source_snapshot.json').read_bytes(),check=True)
 print('PVM_PLACEMENT_OUT='+str(out)+' REMOTE='+host+':'+r,flush=True)
 result=subprocess.run(['ot-run','--mem','32','--threads','16','--disk',str(budget['runtime_gb']),'--dir',r,'--','bash',r+'/run.sh'])
 raise SystemExit(result.returncode)
if __name__=='__main__':main()
