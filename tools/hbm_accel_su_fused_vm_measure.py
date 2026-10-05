#!/usr/bin/env python3
"""Execute one actual saved program slice using real fused VM port RTL."""
import argparse,json,subprocess
from pathlib import Path
import dsrom_su_norm as S
from hbm_accel_su_fused_runtime import bind
from hbm_accel_su_fused_measure import sha

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--cases',type=Path,required=True);ap.add_argument('--case-index',type=int,required=True)
 ap.add_argument('--candidate-index',type=int,default=0);ap.add_argument('--work',type=Path,required=True)
 ap.add_argument('--fp',choices=('dpi','rtl'),default='dpi');a=ap.parse_args()
 a.work.mkdir(parents=True,exist_ok=False)
 plan=bind(a.cases,a.case_index,a.candidate_index,a.work/'fixture')
 if plan['check_words']==0:raise ValueError('retained operations must run before the saved check; not a standalone eligible gate')
 params=dict(plan['params'],MEM_WORDS=plan['memory_words'],CR_WORDS=plan['CR_words'],CHECK_WORDS=plan['check_words'])
 src=[S.ROOT/s for s in S.COMMON+S.FP_SRC[a.fp]]+[S.RTL,
  S.ROOT/'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv',S.ROOT/'rtl/hdc/v41x/ot_dsrom_su_swiglu.sv',
  S.ROOT/'rtl/hbm_accel/su/ot_hbm_accel_su_fused_stream.sv',S.ROOT/'rtl/hbm_accel/su/ot_hbm_accel_su_fused_vm.sv',
  S.ROOT/'rtl/test/tb_hbm_accel_su_fused_vm.sv']
 obj=a.work.resolve()/'obj';cmd=[S.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH',
 '--top-module','tb_hbm_accel_su_fused_vm','-Mdir',str(obj),'-j','16','--unroll-count','4','-fno-dfg',
 *[f'-G{k}={v}' for k,v in params.items()],*map(str,src),'-CFLAGS','-O1']
 pin=dict(plan=plan,command=cmd,source_sha256={str(p.relative_to(S.ROOT)):sha(p) for p in src},fp=a.fp,
  clock_half_period_ns=.416667,SS60_FF25_qualified=False,adopted=False)
 (a.work/'source.json').write_text(json.dumps(pin,indent=2)+'\n')
 with (a.work/'build.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 (a.work/'build.rc').write_text(str(r.returncode)+'\n')
 if r.returncode:return r.returncode
 exe=obj/'Vtb_hbm_accel_su_fused_vm'
 r=subprocess.run([str(exe)],cwd=a.work/'fixture',capture_output=True,text=True)
 (a.work/'run.log').write_text(r.stdout+r.stderr);(a.work/'run.rc').write_text(str(r.returncode)+'\n')
 end=[s for s in r.stdout.splitlines() if s.startswith('VM_END ')]
 metrics={k:int(v) for k,v in (t.split('=') for t in end[-1].split()[1:])} if end else None
 ok=r.returncode==0 and 'PASS' in r.stdout and metrics is not None and metrics['errors']==0 and metrics['debt']==0
 (a.work/'result.json').write_text(json.dumps(dict(source=pin,binary_sha256=sha(exe),terminal=True,
  pass_exact=ok,metrics=metrics,events=[s for s in r.stdout.splitlines() if s.startswith('VM_EVENT ')]),indent=2)+'\n')
 return 0 if ok else 1
if __name__=='__main__':raise SystemExit(main())
