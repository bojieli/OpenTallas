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
    (out/'verdict.json').write_text(json.dumps({'schema':'opentallas.smh-result-valid-gate.v1','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'results':results},indent=2)+'\n')
    return 0 if all(v['ok'] for v in results.values()) else 1
if __name__=='__main__':raise SystemExit(main())
