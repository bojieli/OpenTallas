#!/usr/bin/env python3
"""Compile/run the pinned full K2048 HGI top-k gate; mutant must fail at runtime."""
import argparse,pathlib,subprocess,json,hashlib,sys
p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--mutant',action='store_true');a=p.parse_args()
r=pathlib.Path(__file__).resolve().parents[1];o=pathlib.Path(a.out).resolve();o.mkdir(parents=True,exist_ok=True)
src=[r/'rtl/hbm_accel/generic_20261009/ot_hgi_idx_topk.sv',r/'rtl/test/hbm_generic_20261009/tb_hgi_idx_topk.sv']
(o/'sources.json').write_text(json.dumps({str(s.relative_to(r)):hashlib.sha256(s.read_bytes()).hexdigest() for s in src},indent=2)+'\n')
cmd=['iverilog','-g2012','-s','tb_hgi_idx_topk','-o',str(o/'gate.vvp')]
if a.mutant:cmd+=['-Ptb_hgi_idx_topk.MUTANT=1']
q=subprocess.run(cmd+[str(s) for s in src],capture_output=True,text=True);(o/'compile.log').write_text(q.stdout+q.stderr)
if q.returncode:print('HGI_TOPK BUILD_FAIL');sys.exit(2)
q=subprocess.run(['vvp',str(o/'gate.vvp')],capture_output=True,text=True);(o/'run.log').write_text(q.stdout+q.stderr)
print(q.stdout+q.stderr,end='');(o/'receipt.json').write_text(json.dumps(dict(compile_rc=0,run_rc=q.returncode,mutant=a.mutant))+'\n')
sys.exit(q.returncode)
