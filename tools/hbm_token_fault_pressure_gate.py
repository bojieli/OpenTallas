import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/control/ot_hbm_token_loop.sv','rtl/test/hbm_accel/tb_hbm_token_fault_pressure.sv']
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable fresh evidence path required')
cases=[]
for m in (0,1):
 exe=a.work/f'm{m}.vvp';b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_token_fault_pressure',f'-Ptb_hbm_token_fault_pressure.MUT={m}','-o',str(exe),*[str(ROOT/s) for s in SRC]],capture_output=True,text=True)
 if b.returncode:raise RuntimeError(b.stderr)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(mutant=m,returncode=r.returncode,output=r.stdout))
ok=cases[0]['returncode']==0 and cases[1]['returncode']!=0
record=dict(schema='opentallas.hbm.token_fault_pressure.v1',verdict='PASS' if ok else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC})
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if ok else 1)
