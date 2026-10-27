#!/usr/bin/env python3
"""Smallest combinational transport miter + independent high-address/data/mask mutants."""
import argparse,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RTL=Path('rtl/hbm_next/fused/ot_hnx_fused_vm_native_adapter.sv')
TB=Path('tools/hbm_next/tb_fused_vm_native_adapter.sv')
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',required=True);a=ap.parse_args()
 out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 src=(ROOT/RTL).read_text();cases={'positive':src,
 'mut_high_address':src.replace("{fused_rq_v, 1'b0, fused_rq_sector}","{fused_rq_v, 2'b0, fused_rq_sector[14:0]}"),
 'mut_data':src.replace("fused_wq_data, 8'hff","{1'b0,fused_wq_data[254:0]}, 8'hff"),
 'mut_word_mask':src.replace("8'hff","8'hfe")}
 rows=[]
 for name,text in cases.items():
  p=out/name;p.mkdir(exist_ok=True);rtl=p/'adapter.sv';rtl.write_text(text)
  build=subprocess.run(['iverilog','-g2012','-s','tb_fused_vm_native_adapter','-o',str(p/'sim'),str(rtl),str(ROOT/TB)],capture_output=True,text=True)
  (p/'build.log').write_text(build.stdout+build.stderr)
  if build.returncode:raise RuntimeError(f'{name} compile failed')
  run=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True);(p/'run.log').write_text(run.stdout+run.stderr)
  ok=(run.returncode==0 and 'ADAPTER PASS' in run.stdout) if name=='positive' else run.returncode!=0 and 'mismatch' in run.stdout
  rows.append(dict(name=name,verdict='PASS' if ok else 'FAIL',simulation_exit=run.returncode))
 sha=subprocess.check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip()
 result=dict(source=sha,rtl=str(RTL),bench=str(TB),added_cycles=0,scope='wire mapping only; no bank sharing, timing, or signoff claim',results=rows,verdict='PASS' if all(r['verdict']=='PASS' for r in rows) else 'FAIL')
 (out/'result.json').write_text(json.dumps(result,indent=1)+'\n');print(json.dumps(result,indent=1));return result['verdict']!='PASS'
if __name__=='__main__':raise SystemExit(main())
