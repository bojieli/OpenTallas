import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hbm_accel/control/ot_hbm_token_loop.sv','rtl/hbm_accel/control/ot_hbm_native_ar_token_join.sv','rtl/hbm_accel/qwen/r25/ot_qwen_r25_cmdproc18.sv','rtl/gpu_sys/ds_hbm_full20/ot_ds_hbm_cmdproc20.sv','rtl/test/hbm_accel/tb_hbm_native_ar_token_join.sv']
# struct-close 2026-10-09: OT_ARTOK_SRC (space-separated; index 1 = the DUT file) swaps the sources (registered-boundary wrapper); default unchanged
import os
SRC=os.environ.get('OT_ARTOK_SRC','').split() or SRC
a=argparse.ArgumentParser();a.add_argument('--work',type=Path,required=True);a.add_argument('--out',type=Path,required=True);a=a.parse_args();a.work.mkdir(parents=True,exist_ok=True)
if a.out.exists():raise SystemExit('immutable fresh evidence path required')
cases=[]
vectors=[(q,m,-1,12,0,1234,False) for q in (0,1) for m in (0,1)]
vectors += [(1,0,131070,2,0,524288,False),(1,0,131072,1,0,524288,False),(1,0,151934,1,0,524288,False),(1,0,151935,1,1,524288,False),(1,0,131072,1,0,524288,True)]
for idx,(q,mut,start,ngen,same,pos,truncate_owner) in enumerate(vectors):
  exe=a.work/f'vector{idx}.vvp'
  src=[ROOT/x for x in SRC]
  if truncate_owner:
   replacement=a.work/'owner17_mutant.sv'
   text=src[1].read_text(); needle='launch_pos[k*PW+:PW],launch_token[k*TW+:TW],cp_gen'
   if needle not in text:raise RuntimeError('owner truncation mutant not injected')
   replacement.write_text(text.replace(needle,"launch_pos[k*PW+:PW],(launch_token[k*TW+:TW] & {{(TW-17){1'b0}},{17{1'b1}}}),cp_gen"));src[1]=replacement
  params={'QWEN':q,'MUT':mut,'START_TOKEN':start,'NGEN':ngen,'NEXT_SAME':same,'FIRST_POS':pos}
  b=subprocess.run(['iverilog','-g2012','-s','tb_hbm_native_ar_token_join',*[f'-Ptb_hbm_native_ar_token_join.{k}={v}' for k,v in params.items()],'-o',str(exe),*map(str,src)],capture_output=True,text=True)
  if b.returncode:raise RuntimeError(b.stderr)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
  cases.append(dict(qwen=bool(q),mutant=mut or int(truncate_owner),owner17_truncation=truncate_owner,start_token=start,ngen=ngen,first_pos=pos,returncode=r.returncode,output=r.stdout,verdict='PASS' if r.returncode==0 else 'FAIL'))
ok=all((c['returncode']==0)==(c['mutant']==0) for c in cases)
record=dict(schema='opentallas.hbm.native_ar_token_join.rtl.v1',verdict='PASS' if ok else 'FAIL',cases=cases,source_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC if (ROOT/s).exists()},scope='real two-half32SM CP and token runtime; synthetic SM results; no arithmetic or full token datapath claim')
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record,indent=2));raise SystemExit(0 if ok else 1)
