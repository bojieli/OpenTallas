#!/usr/bin/env python3
"""Run the genuine provider mechanism fixture in an owned scratch output.

Run through ot-run. Provider sources must be the binder's reviewed candidate,
not a behavioral replacement. No production address map or calendar is changed.
"""
import argparse,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--provider-dir',type=Path);a=ap.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
canonical=REPO/'rtl/hbm_accel/loader/service_native/split'
if a.provider_dir is None:a.provider_dir=canonical if(canonical/'ot_hbm_static_load_provider_quad.sv').is_file()else REPO/'results/hbm_bind_1030/static_load'
subprocess.run([sys.executable,str(HERE/'gen_fixture.py'),'--out',str(out)],check=True)
names=['ot_hbm_static_load_provider_quad.sv','ot_hbm_static_load_addr_counter.sv','ot_hbm_static_load_addr_map.sv','ot_hbm_static_load_quad_vehicle.sv']
sources=[a.provider_dir.resolve()/x for x in names]+[out/'tb_provider.sv',REPO/'rtl/hbm_accel/loader/service_native/split/ot_hbm_svc_vmdel_lane_load_static.sv',REPO/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
if any(not p.is_file()for p in sources):raise FileNotFoundError('provider/source dependency missing: '+','.join(str(p)for p in sources if not p.is_file()))
with(out/'build.log').open('w')as f:subprocess.run(['verilator','--binary','--timing','-j','2','-Wno-fatal','--top-module','tb_provider',*map(str,sources),'--Mdir',str(out/'obj')],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
result=[]
for name,arg in [('baseline',None),('wrong_epoch','MUT_EPOCH'),('missing_release','MUT_RELEASE')]:
 cp=subprocess.run([str(out/'obj/Vtb_provider')]+(['+'+arg+'=1']if arg else[]),cwd=out,capture_output=True,text=True);log=cp.stdout+cp.stderr;(out/(name+'.log')).write_text(log)
 if arg:assert cp.returncode!=0 and'PROVIDER_FAULT'in log,log
 else:assert cp.returncode==0 and'PASS GENUINE_PROVIDER_QUAD'in log,log
 result.append(dict(name=name,returncode=cp.returncode,last_lines=log.splitlines()[-3:]))
(out/'run.json').write_text(json.dumps(dict(status='PASS_SOURCE_MECHANISM_ONLY',runs=result),indent=1)+'\n');print(json.dumps(result))
