#!/usr/bin/env python3
"""Build/run the minimum full-width numerical endpoint sender integration gate."""
import argparse,hashlib,json,subprocess
from pathlib import Path
import ha2_hub_credit_gate as source
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--threads',type=int,default=4);a=p.parse_args()
o=a.out.resolve();o.mkdir(parents=True,exist_ok=False)
f=source.PARENT+source.HALF+['rtl/hbm_accel/ha2_ar/tb_ha2_half_endpoint_credit.sv']
pins={s:hashlib.sha256((source.ROOT/s).read_bytes()).hexdigest() for s in f}
(o/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
cmd=['verilator','--binary','--timing','-O0','-Wno-fatal','-Wno-WIDTH','--top-module','tb_ha2_half_endpoint_credit','--Mdir',str(o/'obj'),'--build-jobs',str(a.threads),*f]
(o/'command.json').write_text(json.dumps(cmd,indent=2)+'\n')
with (o/'build.log').open('w') as log:r=subprocess.run(cmd,cwd=source.ROOT,stdout=log,stderr=subprocess.STDOUT)
(o/'build.exit').write_text(str(r.returncode)+'\n')
if r.returncode:raise SystemExit(r.returncode)
with (o/'run.log').open('w') as log:r=subprocess.run([str(o/'obj/Vtb_ha2_half_endpoint_credit')],cwd=source.ROOT,stdout=log,stderr=subprocess.STDOUT)
(o/'run.exit').write_text(str(r.returncode)+'\n')
text=(o/'run.log').read_text();passed=r.returncode==0 and 'PASS_HA2_HALF_ENDPOINT_CREDIT' in text
assert pins=={s:hashlib.sha256((source.ROOT/s).read_bytes()).hexdigest() for s in f}
negatives={}
if passed:
 for mode in ['CORRUPT_GOLDEN','IGNORE_PEER_CREDIT']:
  with (o/(mode+'.log')).open('w') as log:
   neg=subprocess.run([str(o/'obj/Vtb_ha2_half_endpoint_credit'),'+'+mode],cwd=source.ROOT,stdout=log,stderr=subprocess.STDOUT)
  nt=(o/(mode+'.log')).read_text()
  negatives[mode]=dict(returncode=neg.returncode,rejected=neg.returncode!=0 and 'ENDPOINT_FAIL' in nt,output=nt)
 passed=passed and all(n['rejected'] for n in negatives.values())
(o/'terminal.json').write_text(json.dumps(dict(passed=passed,returncode=r.returncode,source_sha256=pins,output=text,negative_controls=negatives),indent=2)+'\n')
print(text)
raise SystemExit(0 if passed else 1)
