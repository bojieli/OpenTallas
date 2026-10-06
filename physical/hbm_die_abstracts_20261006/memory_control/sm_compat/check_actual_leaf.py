#!/usr/bin/env python3
"""Minimum actual smv_leaf elaboration; no arithmetic or timing replay."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parents[4]
a.out.mkdir(parents=True, exist_ok=False)
paths = [
 'rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv',
 'physical/hbm_die_abstracts_20261006/memory_control/sm_compat/ot_hbm_accel_bd_col_bb.v',
 'physical/hbm_die_abstracts_20261006/memory_control/sm_compat/ot_hbm_accel_tc16_bb.v',
 'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v',
]
bench = '''`timescale 1ns/1ps
module tb_actual_leaf;
 parameter integer LBS=2;
 wire gv,gf; wire [31:0] gy; wire [15:0] gt;
 ot_hbm_accel_smv_leaf #(.SUB(4),.LBS(LBS),.LSB(16),.NC(8),.IL(8),
  .TAGW(16),.XD(128),.NBEAT(13),.COL(0),.SP(0),.TCK(1)) u_leaf(
  .clk(1'b0),.rst_n(1'b0),.c_in(22'b0),.w_in({(LBS*266+16*16){1'b0}}),
  .x_ce(1'b0),.x_addr(7'b0),.b_en(1'b0),.b_addr(7'b0),.b_oh(13'b0),
  .b_data(2048'b0),.gv(gv),.gy(gy),.gt(gt),.gf(gf));
 initial begin #1; $display("PASS actual frozen smv_leaf elaboration only"); $finish; end
endmodule
'''
(a.out / 'tb_actual_leaf.sv').write_text(bench)
record = {'scope':'actual smv_leaf branch elaboration; fixed arithmetic macros blackboxed, no numerical or parent timing claim',
 'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
 'parameters':dict(SUB=4,LBS=2,LSB=16,NC=8,IL=8,TAGW=16,XD=128,NBEAT=13,COL=0,SP=0,TCK=1),
 'source_sha256':{s:hashlib.sha256((root/s).read_bytes()).hexdigest() for s in paths},
 'cases':[], 'parent_qualified':False}
with tempfile.TemporaryDirectory(prefix='codex-h17-actual-leaf-') as tmp:
 for name,lbs in [('actual_fixed_shape',2),('actual_unsupported_LBS1',1)]:
  binary=Path(tmp)/f'{name}.vvp'
  cmd=['iverilog','-g2012','-s','tb_actual_leaf',f'-Ptb_actual_leaf.LBS={lbs}','-o',str(binary),*[str(root/s) for s in paths],str(a.out/'tb_actual_leaf.sv')]
  c=subprocess.run(cmd,text=True,capture_output=True)
  (a.out/f'{name}_compile.log').write_text(c.stdout+c.stderr)
  case={'name':name,'LBS':lbs,'compile_exit':c.returncode,'command':cmd}
  if c.returncode==0:
   r=subprocess.run(['vvp',str(binary)],text=True,capture_output=True)
   (a.out/f'{name}_run.log').write_text(r.stdout+r.stderr)
   case['run_exit']=r.returncode
   case['accepted']=r.returncode==0 and 'PASS actual frozen' in r.stdout if lbs==2 else r.returncode!=0 and 'unsupported fixed hardened macro shape' in r.stdout
   vvp=binary.read_text()
   case['actual_branches']=[x for x in ['g_hbdk','g_hardk','g_sbd','g_k'] if f'"{x}"' in vvp]
  else: case['accepted']=False
  record['cases'].append(case)
record['verdict']='PASS' if all(c['accepted'] for c in record['cases']) else 'FAIL'
(a.out/'receipt.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'verdict':record['verdict'],'cases':record['cases']},indent=2))
raise SystemExit(0 if record['verdict']=='PASS' else 1)
