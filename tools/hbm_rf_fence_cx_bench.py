#!/usr/bin/env python3
"""Remote full4096 RF fence transaction bench and actual skid mechanism."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from hbm_rf_fence_cx_model import model
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/gpu/ot_gpu_rf_visibility_fence.sv','physical/hbm_mtp/rtl/ot_hfd_mtp_skid.sv','physical/hbm_mtp/rtl/ot_hfd_mtp_skid_banked_cx.sv','physical/hbm_mtp/rtl/ot_gpu_rf_visibility_fence_cx.sv','physical/hbm_mtp/bench/tb_fence_cx.sv','physical/hbm_mtp/bench/tb_skid_cx.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);a=p.parse_args();a.work.mkdir(parents=True,exist_ok=False)
 (a.work/'model_before_build.json').write_text(json.dumps(model(),indent=2)+'\n')
 rec=dict(source_commit=os.environ['PINNED_SOURCE_COMMIT'],source_failure='mtp_fence_p-d30fa5f39-tc',input_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC+['tools/hbm_rf_fence_cx_model.py','tools/uarch_model.py']},scope='full4096 transaction streams vs original fence; cycle-exact4114bit skid valid/data under stalls and promotion; no control protection or new protocol',cases=[],verdict='INCOMPLETE',adopted=False)
 out=a.work/'record.json'
 def save():out.write_text(json.dumps(rec,indent=2)+'\n')
 save()
 cases=[('fence'+str(seed),'tb_fence_cx',seed,0,False) for seed in [7,3,11,29]]+[('fence_mutant','tb_fence_cx',7,1,True),('skid','tb_skid_cx',0,0,False),('skid_mutant','tb_skid_cx',0,1,True)]
 for name,top,seed,mut,negative in cases:
  exe=a.work/(name+'.vvp');args=['iverilog','-g2012','-s',top,f'-P{top}.MUT={mut}']
  if top=='tb_fence_cx':args+=[f'-P{top}.SEED={seed}']
  with (a.work/(name+'.build.log')).open('w') as log:cp=subprocess.run(['/usr/bin/time','-v','-o',str(a.work/(name+'.build.resources'))]+args+['-o',str(exe)]+[str(ROOT/s) for s in SRC],stdout=log,stderr=subprocess.STDOUT)
  row=dict(name=name,negative=negative,build_exit=cp.returncode,passed=False)
  if cp.returncode==0:
   lp=a.work/(name+'.run.log')
   with lp.open('w') as log:cp=subprocess.run(['/usr/bin/time','-v','-o',str(a.work/(name+'.run.resources')),'vvp','-n',str(exe)],stdout=log,stderr=subprocess.STDOUT)
   raw=lp.read_text();marker='FENCE_CX' if top=='tb_fence_cx' else 'SKID_CX'
   passed=(marker+' FAIL' in raw) if negative else cp.returncode==0 and marker+' PASS' in raw
   row.update(run_exit=cp.returncode,passed=passed,raw_sha256=hashlib.sha256(lp.read_bytes()).hexdigest())
  rec['cases'].append(row);save()
 rec['verdict']='PASS' if all(c['passed'] for c in rec['cases']) else 'FAIL';save();print(rec['verdict'],flush=True);return int(rec['verdict']!='PASS')
if __name__=='__main__':raise SystemExit(main())
