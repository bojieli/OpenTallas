#!/usr/bin/env python3
"""Run the actual one-bit fault-stage DUT or a source mutation; no fake views."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
 p.add_argument('--mode',choices=['normal','missing','bitflip'],default='normal');a=p.parse_args()
 src=ROOT/'rtl/physical/qkd_kv_fault_stage.sv';tb=ROOT/'rtl/test/qwen_static_kv/tb_qkd_kv_fault_stage.sv'
 raw=src.read_text();body='always @(posedge ck) b <= a;'
 if raw.count(body)!=1:raise ValueError('actual source relay body changed')
 if a.mode=='missing':raw=raw.replace(body,'always @* b = a;')
 if a.mode=='bitflip':raw=raw.replace(body,'always @(posedge ck) b <= ~a;')
 a.out.mkdir(parents=True,exist_ok=True);mut=a.out/'dut.sv';mut.write_text(raw)
 exe=a.out/'bench.vvp'
 c=subprocess.run(['iverilog','-g2012','-s','tb_qkd_kv_fault_stage','-o',str(exe),str(mut),str(tb)],capture_output=True,text=True)
 (a.out/'compile.log').write_text(c.stdout+c.stderr)
 if c.returncode:raise RuntimeError(c.stdout+c.stderr)
 r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
 (a.out/'runtime.log').write_text(r.stdout+r.stderr)
 (a.out/'receipt.json').write_text(json.dumps(dict(mode=a.mode,exit_code=r.returncode,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (src,tb,Path(__file__))},mutated_source_sha256=hashlib.sha256(mut.read_bytes()).hexdigest(),claim='Component one fault-observation edge only; no parent/native/physical qualification'),indent=2)+'\n')
 print(r.stdout+r.stderr,end='');return r.returncode
if __name__=='__main__':raise SystemExit(main())
