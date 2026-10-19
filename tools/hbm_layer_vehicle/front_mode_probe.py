#!/usr/bin/env python3
"""Build the actual selected frontend only, with validity/split stimulus."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,time
p=argparse.ArgumentParser();p.add_argument('--bundle',required=True);p.add_argument('--work',required=True)
a=p.parse_args();root=Path(__file__).resolve().parents[2];bundle=Path(a.bundle);work=Path(a.work);work.mkdir(parents=True,exist_ok=True)
files=[bundle/s for s in json.loads((bundle/'master_files.json').read_text())['ot_hbm_accel_smh_attn']]
front=next(f for f in files if f.name=='ot_hbm_sm_attn_front_static.sv')
front_hash=hashlib.sha256(front.read_bytes()).hexdigest()
assert front_hash=='379dc1eadcd4365e0d955dd7755da55893e7aa647aaac1b6f140dad09e5b92c2','selected frontend changed: audit table before probe'
files += [root/'rtl/hbm_accel/loader/service_native/ot_hbm_svc_command_class_guard.sv',root/'rtl/test/hbm_accel/svg_rel/tb_actual_front_modes.sv']
vl=os.path.expanduser('~/.local/opentallas-tools/verilator-5.050/bin/verilator');obj=work/'obj';exe=obj/'Vtb_actual_front_modes'
cmd=[vl,'--binary','--timing','-j','16','-O1','-CFLAGS','-O1','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN','--unroll-count','256','--top-module','tb_actual_front_modes','--Mdir',str(obj)]
cmd += ['-D'+d for d in ['OT_SMH_FC_HIER','OT_SMH_HIER','OT_SMH_XLK','OT_FP_DATA_NORST','OT_SMH_DRST0','OT_SMH_RSTRELAY']]
cmd += ['-I'+str(f.parent) for f in sorted(set(files))]+[str(f) for f in files]
t=time.time();b=subprocess.run(cmd,text=True,capture_output=True);(work/'build.log').write_text(' '.join(cmd)+'\n'+b.stdout+b.stderr)
if b.returncode:raise SystemExit('frontend probe build failed')
r=subprocess.run([str(exe)],text=True,capture_output=True);log=r.stdout+r.stderr;(work/'run.log').write_text(log)
report=dict(frontend=str(front),frontend_sha256=front_hash,rc=r.returncode,pass_='ACTUAL_FRONT_MODES_PASS' in log and r.returncode==0,wall_seconds=time.time()-t,
    executable_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),scope='actual selected frontend validity/sticky state and literal split streams; no GO/transport implementation instantiated')
(work/'receipt.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));raise SystemExit(0 if report['pass_'] else 1)
