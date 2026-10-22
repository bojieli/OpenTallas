#!/usr/bin/env python3
"""Fleet-only source reset theorem: arithmetic outputs are arbitrary every edge, all state starts free."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--root',required=True);ap.add_argument('--out',required=True);ap.add_argument('--mut',type=int,default=0);ap.add_argument('--reset-pin',type=int,default=0);a=ap.parse_args()
r=Path(a.root).resolve();o=Path(a.out).resolve();o.mkdir(parents=True,exist_ok=True)
p=r/'rtl/hdc/nearhbm/ot_qwen_tp8_pv_join_cold_t.sv';s=p.read_text()
old='output reg[511:0] y,output reg y_valid,output reg fault\n'
assert s.count(old)==1
s=s.replace(old,'output reg[511:0] y,output reg y_valid,output reg fault,output wire cold_zero\n')
s=s.replace('\nendmodule','\n assign cold_zero=(xr==512\'d0)&&(yr==512\'d0)&&(y==512\'d0);\nendmodule')
(o/'proof.v').write_text(s)
(o/'adder_any.v').write_text('''module ot_hdc_fp32_add_lat #(parameter LAT=7,DRST=0)(input clk,rst_n,valid_in,input[31:0]a,b,output[31:0]y,output[1:0]err,output valid_out);
(* anyseq *) wire[31:0] arbitrary_y; (* anyseq *) wire[1:0] arbitrary_err; (* anyseq *) wire arbitrary_valid;
assign y=arbitrary_y;assign err=arbitrary_err;assign valid_out=arbitrary_valid;endmodule
''')
ys=['read_verilog -formal -sv proof.v adder_any.v',f'chparam -set COLD_INIT 1 -set MUT {a.mut} -set RESET_PIN {a.reset_pin} ot_qwen_tp8_pv_join_cold_t','hierarchy -check -top ot_qwen_tp8_pv_join_cold_t','proc','flatten','async2sync','opt_clean','sat -seq 6 '+' '.join(f'-set-at {i} rst_n 0' for i in range(1,7))+' -set-def-inputs -prove cold_zero 1 -prove-skip 3 -verify -dump_json cex.json -show-ports']
(o/'proof.ys').write_text('\n'.join(ys)+'\n')
with (o/'proof.log').open('w') as f:ret=subprocess.run(['yosys','-s','proof.ys'],cwd=o,stdout=f,stderr=subprocess.STDOUT)
log=(o/'proof.log').read_text();res={'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'mut':a.mut,'arithmetic_model':'independent arbitrary y/err/valid per lane per edge; stronger than actual arithmetic','initial_state':'all free; no zero-init or paired-start assumption','reset_edges':6,'checked_steps':[4,5,6],'reset_pin':a.reset_pin,'proven':ret.returncode==0 and 'SUCCESS!' in log,'rc':ret.returncode,'qualification':'source reset theorem only; mapped native closure/census and full proof owed'}
(o/'result.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(res));raise SystemExit(0 if res['proven'] else 1)
