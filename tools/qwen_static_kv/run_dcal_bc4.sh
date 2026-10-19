#!/bin/bash
set -euo pipefail
O=$(realpath -m "$1"); MUT=${2:-0};mkdir -p "$O"
D=rtl/qwen_sys/d2d_static_20261015
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
python3 - "$O" "$MUT" <<'PY'
from pathlib import Path
import sys
O=Path(sys.argv[1]);mut=int(sys.argv[2]);D=Path('rtl/qwen_sys/d2d_static_20261015')
s=(D/'qkd_d2d_cal_seq_bootcfg.sv').read_text().replace('module qkd_d2d_cal_seq_pin_bc #(','module qkd_d2d_cal_seq_pin_bc__ot_pr_core #(')
(O/'frozen_core.sv').write_text(s)
candidate=(D/'qkd_d2d_cal_seq_bc4.sv').read_text()
if mut==1: candidate=candidate.replace('land1 <= {4{land0}}', 'land1 <= {4{rst_n}}')
if mut==2: candidate=candidate.replace('if (!rel1[18]) fault <= 0', 'if (!rel1[18]) fault <= 1').replace('if (!rel1[18]) f_early <= 0', 'if (!rel1[18]) f_early <= 1')
if mut==3: candidate=candidate.replace("cfg_data[14:0] <= ((32'(0)) >> 0)", "cfg_data[14:0] <= 1")
# A guaranteed payload-reset corruption independent of the generated chunk alignment.
if mut==3:
 import re
 candidate=re.sub(r'(if \(!rel1\[\d+\]\) cfg_data\[[^]]+\] <= )[^;]+;',r'\g<1>1;',candidate,count=1)
(O/'candidate.sv').write_text(candidate)
ports={'cfg_tx_we':1,'cfg_rx_we':1,'cfg_addr':6,'cfg_data':32,'cal_start':1,'cal_seg':1,'cal_ready':1,'running':1,'layer':6,'adm_done':1,'tok_start':1,'fault':1}
s='''`timescale 1ns/1ps
module tb_dcal_bc4;
`include "d2d_cal_image_mu.svh"
reg ck=0; always #5 ck=~ck;
reg rst_n=0,reload=0,epoch_go=0,halt=0,bcfg_tx_we=0,bcfg_rx_we=0;
reg [5:0] bcfg_addr=0; reg [31:0] bcfg_data=0;
'''
for prefix in ['a','b']:
 for n,w in ports.items():s+=f'wire [{w-1}:0] {prefix}_{n};\n'
for prefix,mod in [('a','qkd_d2d_cal_seq_pin_bc'),('b','qkd_d2d_cal_seq_pin_bc4')]:
 ps=[f'.{n}({n})' for n in ['ck','rst_n','reload','epoch_go','halt','bcfg_tx_we','bcfg_rx_we','bcfg_addr','bcfg_data']]+[f'.{n}({prefix}_{n})' for n in ports]
 
 if prefix=='b' and mut in [4,5,6]: mod+= {4:'#(.EP_SKEW(2))',5:'#(.GO_OFS(1))',6:"#(.START_ADJ(720'd1))"}[mut]
 s+=mod+' u_'+prefix+' ('+','.join(ps)+');\n'
a='{'+','.join('a_'+n for n in ports)+'}';b='{'+','.join('b_'+n for n in ports)+'}'
s+='''integer cyc=0,checked=0,reset_count=0,ncal=0,nfault=0,wordidx=0; reg [31:0] rng=32'h9e3779b9;
initial begin
 repeat(8) @(negedge ck); rst_n=1;
 for(cyc=0;cyc<600000;cyc=cyc+1) begin
  @(negedge ck);
  rng = (rng << 1) ^ (rng[31] ? 32'h04c11db7 : 0);
  // Two long production epochs, then adversarial reload/halt/reset/data activity.
  epoch_go = (cyc==100 || cyc==280000 || cyc>560000 && cyc%1200==200);
  if(cyc>560000) begin
   rst_n = !(cyc%2003 < 4); reload=(rng[6:0]==0); halt=(rng[11:0]==0);
   bcfg_tx_we=rng[5:0]==1;bcfg_rx_we=rng[5:0]==2;bcfg_addr=rng[11:6];bcfg_data=rng;
  end else begin
   bcfg_tx_we=0;bcfg_rx_we=0;bcfg_data=rng;bcfg_addr=rng[5:0];
   if(cyc>=8 && cyc<74) begin
    wordidx=cyc-8; bcfg_tx_we=!wordidx[0];bcfg_rx_we=wordidx[0];
    bcfg_addr=wordidx<64 ? (wordidx>>1) : 32;
    if(wordidx<64) bcfg_data=wordidx[0] ? D2D_CAL_K_RX_IMG[32*(wordidx>>1) +:32] : D2D_CAL_K_TX_IMG[32*(wordidx>>1) +:32];
    else bcfg_data=wordidx[0] ? D2D_CAL_K_RX_SEG2 : D2D_CAL_K_TX_SEG2;
   end
  end
  if(!rst_n) reset_count=reset_count+1;
  #1;
'''+f'  if ({a} !== {b}) $fatal(1,"BC4_MITER mismatch edge %0d a=%h b=%h",cyc,{a},{b});\n'+'''
  checked=checked+1; ncal=ncal+b_cal_start;nfault=nfault+b_fault;
 end
 $display("BC4_MITER_PASS edges=%0d all_public_bits=53 resets=%0d starts=%0d fault_edges=%0d",checked,reset_count,ncal,nfault);$finish;
end
endmodule
'''
(O/'miter.sv').write_text(s)
PY
"$VL" --binary --timing -O1 -Wno-fatal -j 4 -I$D --top-module tb_dcal_bc4 --Mdir "$O/obj" \
 "$O/frozen_core.sv" results/arch/kv_dcal_bc3safe_1019/frozen_outer_wrapper.v \
 $D/ot_qwen_d2d_cal_seq.sv $D/ot_qwen_d2d_cal_seq_dies_mu.sv \
 $D/ot_qwen_d2d_cal_seq_bc4.sv "$O/candidate.sv" "$O/miter.sv" > "$O/build.log" 2>&1
"$O/obj/Vtb_dcal_bc4" | tee "$O/run.log"
