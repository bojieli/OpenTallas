#!/usr/bin/env python3
from pathlib import Path
import subprocess,json
import argparse
ap=argparse.ArgumentParser(description="Check static landing epoch origins, default lockstep, and wrong-bias mutants.")
ap.add_argument('--work',required=True,type=Path);ap.add_argument('--verilator',default='verilator');a=ap.parse_args()
W=a.work.resolve();W.mkdir(parents=True,exist_ok=False);V=a.verilator;rows=[]
ROOT=Path(__file__).resolve().parents[2]
TB=ROOT/'tools/s81_dv/tb_pl_land_epoch.sv'
RTL=ROOT/'rtl/common/landed_parent'

cases=[('d4_equal',4,0,0,True),('d4_skew_fail',4,6,0,False),('d4_bias',4,6,6,True),('d4_mutant',4,6,5,False),('d4_reverse',4,-6,2,True),('d4_bias5',4,5,5,True),('d4_reverse5',4,-5,3,True),('d8_equal',8,0,0,True),('d8_bias',8,6,6,True),('d8_reverse',8,-6,10,True),('d8_mutant',8,6,5,False)]
for d,b in sorted(set((x[1],x[3]) for x in cases)):
 pref='v2_d'+str(d)+'b'+str(b);cmd=[V,'--binary','--timing','--assert','-Wno-fatal','--top-module','tb','-GDEPTH='+str(d),'-GBIAS='+str(b),'-Mdir',str(W/pref),'-j','1',str(TB),str(RTL/'ot_pl_land.sv'),str(RTL/'ot_pl_land_kept_enable.sv')]
 with (W/(pref+'.build.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 assert q.returncode==0,(d,b)
for label,d,s,b,want in cases:
 with (W/(label+'.v2.log')).open('w') as f:q=subprocess.run([str(W/('v2_d'+str(d)+'b'+str(b))/'Vtb'),'+SKEW='+str(s)],cwd=W,stdout=f,stderr=subprocess.STDOUT)
 txt=(W/(label+'.v2.log')).read_text();rows.append(dict(label=label,depth=d,skew=s,bias=b,rc=q.returncode,expected_pass=want,correct=(q.returncode==0)==want,diagnosis=next((x for x in txt.splitlines() if 'LAND_ORIGIN_PASS' in x or 'LAND_FAULT' in x or 'LAND_DATA' in x or 'DEFAULT_REFERENCE' in x),'')));print(rows[-1],flush=True)
for d,b in [(4,8),(4,-1),(6,0)]:
 label='invalid_d'+str(d)+'b'+str(b);cmd=[V,'--lint-only','--timing','-Wno-fatal','--top-module','tb','-GDEPTH='+str(d),'-GBIAS='+str(b),str(TB),str(RTL/'ot_pl_land.sv'),str(RTL/'ot_pl_land_kept_enable.sv')]
 with (W/(label+'.log')).open('w') as f:q=subprocess.run(cmd,cwd=W,stdout=f,stderr=subprocess.STDOUT)
 txt=(W/(label+'.log')).read_text();ok=q.returncode!=0 and 'REQUIRES_POWER_OF_TWO_DEPTH_AND_STATIC_EPOCH_BIAS' in txt;rows.append(dict(label=label,rc=q.returncode,correct=ok));print(rows[-1],flush=True)
(W/'result_v2.json').write_text(json.dumps(rows,indent=2)+'\n')
raise SystemExit(0 if all(x['correct'] for x in rows) else 1)
