#!/usr/bin/env python3
"""Source-pinned minimum allocated-block controller gate, on admitted remote."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/control/ot_hbm_native_index_control.sv','rtl/test/hbm_accel/tb_hbm_native_index_control.sv','tools/hbm_native_index_control_model.py']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
 rec=dict(source_commit=os.environ['PINNED_SOURCE_COMMIT'],input_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC},scope='minimum controller only; receipt is test actor; actual service join separately measured',cases=[],verdict='INCOMPLETE',adopted=False)
 out=a.work/'record.json'
 def save():out.write_text(json.dumps(rec,indent=2)+'\n')
 save();exe=a.work/'control.vvp'
 with (a.work/'build.log').open('w') as log:
  cp=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_index_control','-Ptb_hbm_native_index_control.PREFETCH_CASE=1','-o',str(exe)]+[str(ROOT/s) for s in SRC if s.endswith('.sv')],stdout=log,stderr=subprocess.STDOUT)
 rec['build_exit']=cp.returncode;save()
 if cp.returncode:rec['verdict']='BUILD_FAIL';save();return 1
 for name,arg,marker in [('dynamic24',None,'PASS_NATIVE_INDEX_CONTROL frames=24'),('identity','+BAD_PREFETCH','EXPECTED_PREFETCH_IDENTITY_REJECT'),('empty','+BAD_BLOCKS=0','EXPECTED_BLOCKCOUNT_REJECT blocks=0'),('oversize','+BAD_BLOCKS=343','EXPECTED_BLOCKCOUNT_REJECT blocks=343')]:
  lp=a.work/(name+'.log')
  with lp.open('w') as log:cp=subprocess.run(['/usr/bin/time','-v','-o',str(a.work/(name+'.resources')),'vvp',str(exe)]+([arg] if arg else []),stdout=log,stderr=subprocess.STDOUT)
  raw=lp.read_text();rec['cases'].append(dict(name=name,exit=cp.returncode,passed=cp.returncode==0 and marker in raw,raw_sha256=hashlib.sha256(lp.read_bytes()).hexdigest()));save()
 rec['verdict']='PASS' if all(c['passed'] for c in rec['cases']) else 'FAIL';save();print(rec['verdict']);return int(rec['verdict']!='PASS')
if __name__=='__main__':raise SystemExit(main())
