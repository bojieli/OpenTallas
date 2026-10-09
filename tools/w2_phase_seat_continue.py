"""Continue the live pinned calibration only after its actual process exits."""
import json,os,time,subprocess,glob
from pathlib import Path
base=Path('/srv/opentallas-scratch2/scratch/codex/w2-phase-seat-19a1b52dc');src=base/'src'
pid=2409627
while True:
    try:os.kill(pid,0)
    except ProcessLookupError:break
    time.sleep(15)
cal=base/'physical_no2_cal'
term=cal/'terminal.json'
if not term.exists() or json.loads(term.read_text()).get('exit_code')!=0:
    (base/'continuation.terminal.json').write_text(json.dumps(dict(status='CALIBRATION_FAILED_PRESERVED',terminal=json.loads(term.read_text()) if term.exists() else None),indent=2)+'\n');raise SystemExit(1)
bases=list(cal.glob('work/orfs/results/asap7/*/base'))
if len(bases)!=1:raise SystemExit('missing/ambiguous real calibration base')
subprocess.run(['python3','tools/closure_loop/ck_insertion.py','--base',str(bases[0]),'--clock','clk_sm','--route-corner','TC','--image','openroad/orfs:asap7lock','--output',str(base/'calib.json')],cwd=src,check=True)
env=os.environ.copy();env.update({k:str(v) for k,v in json.loads((base/'calib.json').read_text())['env'].items()})
env.update(CL_PHASE='route',OT_ORFS_CORNER_OVERRIDE='TC',OT_ROUTE_HOLD_CORNERS='mm',OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl')
route=base/'physical_no2_route'
cmd=['python3','physical/hbm_w2_rb_station_20261006/run_owned.py','--run',str(route),'--no','2','--safe','--phase-seat','--core-width','480','--core-height','200','--place-density','0.40','--period-ps','730','--hold-margin-ns','0.010','--threads','16','--tag','codex_W2_phase_seat']
p=subprocess.run(cmd,cwd=src,env=env)
if list(route.glob('work/orfs/results/asap7/*/base/6_final.odb')):
    subprocess.run(['python3','physical/hbm_w2_rb_station_20261006/signoff.py','--run',str(route)],cwd=src,env=env)
(base/'continuation.terminal.json').write_text(json.dumps(dict(status='ROUTE_RETURNED',source_commit='19a1b52dc',route_exit=p.returncode,signoff=str(route/'signoff.json'),adoption=False),indent=2)+'\n')
