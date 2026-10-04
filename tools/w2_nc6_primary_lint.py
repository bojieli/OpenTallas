#!/usr/bin/env python3
"""Snapshot and lint the actual primary composition; never run a fixture."""
from pathlib import Path
import argparse,subprocess,json,time,hashlib
ROOT=Path(__file__).resolve().parents[1]
def run(out,helper):
 out.mkdir(parents=True,exist_ok=False)
 src=[ROOT/'rtl/experimental/w2_nc6_protection_20261003/ot_w2_sealed_secded72.sv',ROOT/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_coded_secondary_acyclic.sv',helper,ROOT/'rtl/experimental/w2_nc6_primary_20261003/ot_w2_nc6_protected_completion.sv']
 h=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 snaps=[]
 for i,p in enumerate(src):
  q=out/f'input_{i}_{p.name}';q.write_bytes(p.read_bytes());snaps.append(q)
 compiler=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator')
 argv=[str(compiler),'--lint-only','--Wall','-Wno-fatal','--top-module','ot_w2_nc6_protected_completion','-GOPT_EXACT=1',*[str(q) for q in snaps]]
 r={'argv':argv,'sources':{str(p):h(q) for p,q in zip(src,snaps)},'compiler_sha256':h(compiler),'scope':'split-cone syntax/SCC diagnosis only; no fullfixture run','caps':'none','start_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())}
 (out/'start.json').write_text(json.dumps(r,indent=2)+'\n');t=time.monotonic()
 with (out/'lint.log').open('w') as log:cp=subprocess.run(argv,stdout=log,stderr=subprocess.STDOUT)
 log=(out/'lint.log').read_text()
 r.update(exit_code=cp.returncode,elapsed_s=time.monotonic()-t,unoptflat_count=log.count('%Warning-UNOPTFLAT'),latch_count=log.count('%Warning-LATCH'))
 (out/'receipt.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
 return cp.returncode
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--helper',type=Path,required=True);a=p.parse_args();raise SystemExit(run(a.out.resolve(),a.helper.resolve()))
