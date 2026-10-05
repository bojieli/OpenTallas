#!/usr/bin/env python3
"""One changed finite-provider gate, cached operands/checks only; no oracle."""
import argparse,json,subprocess
from pathlib import Path
import dsrom_su_norm as S
from hbm_accel_su_fused_runtime import bind_finite_norm
from hbm_accel_su_fused_measure import sha


def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--cases',type=Path,required=True);ap.add_argument('--case-index',type=int,default=1)
 ap.add_argument('--candidate-index',type=int,default=0);ap.add_argument('--work',type=Path,required=True)
 a=ap.parse_args();a.work.mkdir(parents=True,exist_ok=False)
 plan=bind_finite_norm(a.cases,a.case_index,a.candidate_index,a.work/'fixture')
 paths=S.COMMON+S.FP_SRC['dpi']+['rtl/hdc/v41x/ot_dsrom_su_norm.sv',
  'rtl/hdc/v41x/ot_dsrom_su_hcpost.sv','rtl/hdc/v41x/ot_dsrom_su_swiglu.sv',
  'rtl/hbm_accel/su/ot_hbm_accel_su_fused_stream.sv',
  'rtl/hbm_accel/su/ot_hbm_accel_su_fused_mreq.sv',
  'rtl/test/tb_hbm_accel_su_fused_mreq.sv',
  'rtl/link/ot_link_afifo.sv','rtl/gpu_sys/ot_gpu_cdc_fifo.sv','rtl/gpu_sys/ot_gpu_mreq_cdc.sv',
  'rtl/gpu_sys/ot_gpu_xbar.sv','rtl/gpu_sys/ot_gpu_l2_slice.sv',
  'rtl/gpu_sys/ot_gpu_hbm_partition.sv','rtl/gpu_sys/ot_gpu_memsys.sv',
  'rtl/hdc/kv/ot_hdc_hbm_model.sv']
 src=[S.ROOT/p for p in dict.fromkeys(paths)]
 params={k:plan['params'][k] for k in ('N','D','KIND')}
 obj=a.work.resolve()/'obj'
 cmd=[S.VERILATOR,'--binary','--timing','-O2','-Wno-fatal','-Wno-WIDTH',
  '--top-module','tb_hbm_accel_su_fused_mreq','-Mdir',str(obj),'-j','16',
  '--unroll-count','4','-fno-dfg',*[f'-G{k}={v}' for k,v in params.items()],*map(str,src),'-CFLAGS','-O1']
 pin=dict(command=cmd,source_sha256={str(p.relative_to(S.ROOT)):sha(p) for p in src},
  plan=plan,arithmetic='existing DPI primitive functional gate; no physical closure credit',
  clk_SU_period_ns=.833334,clk_mem_period_ns=1,actual_parent_program_bound=False,
  baseline_family_rerun=False,SS60_FF25_qualified=False,adopted=False)
 (a.work/'source.json').write_text(json.dumps(pin,indent=2)+'\n')
 with (a.work/'build.log').open('w') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 (a.work/'build.rc').write_text(str(r.returncode)+'\n')
 if r.returncode:return r.returncode
 exe=obj/'Vtb_hbm_accel_su_fused_mreq';runs=[]
 # One ordinary cached-source command, one changed-boundary foreign-tag check.
 # Same binary/source. No family arithmetic sweep or repeated native program.
 for name,args in [('actual',[]),('foreign_tag',['+NEG=1'])]:
  r=subprocess.run([str(exe),*args],cwd=a.work/'fixture',capture_output=True,text=True)
  (a.work/f'{name}.log').write_text(r.stdout+r.stderr);(a.work/f'{name}.rc').write_text(str(r.returncode)+'\n')
  end=[s for s in r.stdout.splitlines() if s.startswith('FINITE_END ')]
  metrics={k:float(v) if '.' in v else int(v) for k,v in (t.split('=') for t in end[-1].split()[1:])} if end else None
  ok=r.returncode==0 and ('\nPASS\n' in r.stdout if name=='actual' else 'FINITE_NEGATIVE_PASS' in r.stdout)
  runs.append(dict(name=name,rc=r.returncode,pass_exact=ok,metrics=metrics,
   events=[s for s in r.stdout.splitlines() if s.startswith('FINITE_EVENT ')]))
 result=dict(source=pin,binary_sha256=sha(exe),terminal=True,runs=runs,
  pass_exact=all(r['pass_exact'] for r in runs),mixed_original_fused_program_measured=False,
  actual_parent_program_bound=False,adopted=False)
 (a.work/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 return 0 if result['pass_exact'] else 1


if __name__=='__main__':raise SystemExit(main())
