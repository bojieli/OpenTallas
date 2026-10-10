#!/usr/bin/env python3
"""Minimum full-NC8 SM south-front consumer gate, including named negative controls."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    source=ROOT/'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv'
    full=source.read_text();code=full[full.index('module ot_hbm_accel_smh_result_valid #('):]
    variants={'good':code,'no_fault_valid_mask':code.replace('(faults & valids)','faults'),
      'column0_retire':code.replace('ENABLE ? all_valid : valids[0]','ENABLE ? valids[0] : valids[0]'),
      'no_coherence_fault':code.replace(' | partial_valid','')}
    results={}
    for name,text in variants.items():
      sv=out/(name+'.sv');sv.write_text(text);binary=out/(name+'.vvp')
      subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(sv),str(ROOT/'rtl/hbm_accel/sm/result_valid/tb.sv')],check=True)
      run=subprocess.run(['vvp',str(binary)],text=True,capture_output=True);(out/(name+'.log')).write_text(run.stdout+run.stderr)
      ok=run.returncode==0 if name=='good' else run.returncode!=0 and 'QUALIFY_FAIL' in run.stdout
      results[name]={'rc':run.returncode,'ok':ok,'source_sha256':hashlib.sha256(text.encode()).hexdigest()}
      print(name,'PASS' if ok else 'FAIL')
    binary=out/'front_s.vvp'
    sources=['rtl/hbm_accel/sm/result_valid/tb_front_s.sv',
      'rtl/hbm_accel/sm/ot_hbm_accel_smh.sv','rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
      'rtl/hbm_accel/sm/ot_hbm_accel_issue_pq.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
    subprocess.run(['iverilog','-g2012','-s','tb_front_s','-o',str(binary)]+[str(ROOT/p) for p in sources],check=True)
    run=subprocess.run(['vvp',str(binary)],text=True,capture_output=True)
    (out/'front_s_integration.log').write_text(run.stdout+run.stderr)
    results['front_s_integration']={'rc':run.returncode,'ok':run.returncode==0 and 'SM_FRONT_VALID_PASS' in run.stdout}
    print('front_s_integration','PASS' if results['front_s_integration']['ok'] else 'FAIL')
    # negative control: the released unqualified front (RESULT_VALID 0) on the same stale-held-fault / partial-row
    # stimulus must FAIL; and a gated build (OT_SMH_CG, no explicit OT_SMH_RESULT_VALID) must qualify by default
    for name,args in (('front_s_unqualified_negative',['-Ptb_front_s.RV=0']),
                      ('front_s_cg_default',['-Ptb_front_s.RV=-1'])):
      binary=out/(name+'.vvp')
      if name=='front_s_cg_default':
        # RV -1 is not a value: re-elaborate with the define and the module default instead of a forced parameter
        tb=(ROOT/sources[0]).read_text().replace('#(.RESULT_VALID(RV),.NC(8))','#(.NC(8))')
        tbp=out/'tb_front_s_cgdefault.sv';tbp.write_text(tb)
        cmd=['iverilog','-g2012','-DOT_SMH_CG','-s','tb_front_s','-o',str(binary),str(tbp)]+[str(ROOT/p) for p in sources[1:]]
      else:
        cmd=['iverilog','-g2012','-s','tb_front_s']+args+['-o',str(binary)]+[str(ROOT/p) for p in sources]
      subprocess.run(cmd,check=True)
      run=subprocess.run(['vvp',str(binary)],text=True,capture_output=True)
      (out/(name+'.log')).write_text(run.stdout+run.stderr)
      if name=='front_s_cg_default':
        ok=run.returncode==0 and 'SM_FRONT_VALID_PASS' in run.stdout
      else:
        ok=run.returncode!=0 and 'FRONT_QUALIFY_FAIL' in run.stdout+run.stderr
      results[name]={'rc':run.returncode,'ok':ok}
      print(name,'PASS' if ok else 'FAIL')
    (out/'verdict.json').write_text(json.dumps({'schema':'opentallas.smh-result-valid-gate.v1','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'results':results},indent=2)+'\n')
    return 0 if all(v['ok'] for v in results.values()) else 1
if __name__=='__main__':raise SystemExit(main())
