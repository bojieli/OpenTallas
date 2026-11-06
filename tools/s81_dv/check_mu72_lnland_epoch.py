#!/usr/bin/env python3
from pathlib import Path
import subprocess,json
import argparse
ap=argparse.ArgumentParser(description="Check full MU72 landing payloads at selected static reset origins.")
ap.add_argument('--work',required=True,type=Path);ap.add_argument('--verilator',default='verilator');a=ap.parse_args()
W=a.work.resolve();W.mkdir(parents=True,exist_ok=False);V=a.verilator;rows=[]
ROOT=Path(__file__).resolve().parents[2]
fs=['tools/s81_dv/tb_mu72_lnland_epoch.sv','rtl/common/landed_parent/ot_pl_land.sv','rtl/common/landed_parent/ot_pl_land_reset_forest.sv','rtl/common/landed_parent/ot_pl_land_kept_enable.sv','rtl/common/landed_parent/ot_pl_land_field_copies.sv','rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv','physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv']
built={}
for label,s,k,n,expect in [('default0',0,0,0,True),('actual5',5,5,3,True),('actual6',6,6,2,True),('wrong_bias',5,6,4,False),('wrong_latency',6,5,3,False)]:
 if (k,n) not in built:
  cmd=[V,'--binary','--timing','--assert','-Wno-fatal','--top-module','tb','-GKNBIAS='+str(k),'-GNKBIAS='+str(n),'-Mdir',str(W/label),'-j','1']+[str(ROOT/x) for x in fs]
  with (W/(label+'.build.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,stdout=f,stderr=subprocess.STDOUT)
  if q.returncode:print('BUILD_FAIL',label,flush=True);raise SystemExit(q.returncode)
  built[k,n]=W/label/'Vtb'
 with (W/(label+'.run.log')).open('w') as f:q=subprocess.run([str(built[k,n]),'+SKEW='+str(s)],cwd=W,stdout=f,stderr=subprocess.STDOUT)
 txt=(W/(label+'.run.log')).read_text();row=dict(label=label,skew=s,KN_bias=k,NK_bias=n,rc=q.returncode,expected_pass=expect,correct=(q.returncode==0)==expect,diagnosis=next((x for x in txt.splitlines() if 'LNLAND_EPOCH_PASS' in x or 'LAND_FAULT' in x or 'LNLAND_KN_DATA' in x or 'LNLAND_NK_DATA' in x),''));rows.append(row);(W/'result.json').write_text(json.dumps(rows,indent=2)+'\n');print(row,flush=True)
raise SystemExit(0 if all(x['correct'] for x in rows) else 1)
