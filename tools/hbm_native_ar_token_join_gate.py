import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/control/ot_hbm_token_loop.sv','rtl/hbm_accel/control/ot_hbm_native_ar_token_join.sv','rtl/hbm_accel/qwen/r25/ot_qwen_r25_cmdproc18.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv','rtl/test/hbm_accel/tb_hbm_native_ar_token_join.sv']
a=argparse.ArgumentParser();a.add_argument('--work',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable fresh evidence path required')
cases=[]
for q in (0,1):
 for mut in (0,1):
  exe=a.work/f'q{q}m{mut}.vvp'
  b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_ar_token_join',f'-Ptb_hbm_native_ar_token_join.QWEN={q}',f'-Ptb_hbm_native_ar_token_join.MUT={mut}','-o',str(exe),*[str(ROOT/x) for x in SRC]],capture_output=True,text=True)
  if b.returncode:raise RuntimeError(b.stderr)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
  cases.append(dict(qwen=bool(q),mutant=mut,returncode=r.returncode,output=r.stdout,verdict='PASS' if r.returncode==0 else 'FAIL'))
ok=all((c['returncode']==0)==(c['mutant']==0) for c in cases)
record=dict(schema='opentallas.hbm.native_ar_token_join.rtl.v1',verdict='PASS' if ok else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC},scope='real two-half32SM CP and token runtime; synthetic SM results; no arithmetic or full token datapath claim')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if ok else 1)
