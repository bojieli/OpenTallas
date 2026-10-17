#!/usr/bin/env python3
"""Generate a fixed-calendar 32-PC boundary miter, without a DRAM oracle."""
from pathlib import Path
import sys
root=Path(__file__).resolve().parents[2]
# Explicit widths make the external comparison independent of parser elaboration.
inputs={'k_v':1,'k_we':1,'k_addr':30,'k_len':4,'k_tag':17,'k_wdata':256,'k_wstrb':32,'kr_rdy':1,'dram_rvalid':1,'dram_rdata':256}
outputs={'k_rdy':1,'kr_v':1,'kr_tag':17,'kr_beat':4,'kr_data':256,'k_wr_done':1,'row_v':1,'row_op':3,'row_bank':5,'row_row':19,'col_v':1,'col_we':1,'col_bank':5,'col_col':5,'col_data':256,'col_strb':32,'pc_fault':1,'owner_fault':1}
lines=['`timescale 1ns/1ps','module tb; parameter MUT=0; reg clk=0; always #0.5 clk=~clk; reg rst_n=0; integer cyc=0; integer checks=0,cols=0,refs=0; initial begin repeat(5) @(negedge clk); rst_n=1; end','genvar p; generate for(p=0;p<32;p=p+1) begin:g',"localparam integer RP=(p*118/32)%118; localparam integer RELOAD=118+RP+((RP+118+p)%2);"]
for n,w in inputs.items():
 expr={'k_v':'rst_n && cyc>=40 && cyc<3700 && ((cyc-40)%512==0)','k_we':"1'b1",'k_addr':"30'(p*4)",'k_len':"4'd1",'k_tag':"17'(cyc)",'k_wdata':"{8{32'(32'h12340000+p+cyc)}}",'k_wstrb':"32'hffffffff",'kr_rdy':"1'b1",'dram_rvalid':"1'b0",'dram_rdata':"256'b0"}[n]
 lines.append(f"wire [{w-1}:0] {n}={expr};")
for n,w in outputs.items(): lines.append(f'wire [{w-1}:0] a_{n},b_{n};')
lines.append('wire [5:0] b_faults; assign b_owner_fault=|b_faults;')
common=['.clk(clk)','.rst_n(rst_n)']+[f'.{n}({n})' for n in inputs]
for prefix,mod,params,extra in [('a','ot_hbm_svc_pc_ctrl_leaf','.P(p),.PHASE(0)',[]),('b','ot_hbm_svc_pc_ctrl_leaf_cfg_h9','', [".pc_id(5'(p^(MUT==1)))",".refresh_reload(8'(RELOAD^(MUT==2)))"])]:
 pp=f'#({params})' if params else ''
 lines.append(f'{mod} {pp} {prefix}('+','.join(common+extra+[('.owner_fault_split(b_faults)' if prefix=='b' and n=='owner_fault' else f'.{n}({prefix}_{n})') for n in outputs])+');')
# Output payloads have no valid meaning before their valid qualifier.
comp=['k_rdy','kr_v','k_wr_done','row_v','col_v','pc_fault','owner_fault']
lines+=['always @(negedge clk) if(rst_n && cyc>12) begin', 'checks=checks+1;', "if({"+','.join('a_'+n for n in comp)+'} !== {'+','.join('b_'+n for n in comp)+'}) $fatal(1,"PC_CFG_MISMATCH pc=%0d cycle=%0d mut=%0d",p,cyc,MUT);', 'if(a_row_v && {a_row_op,a_row_bank,a_row_row} !== {b_row_op,b_row_bank,b_row_row}) $fatal(1,"PC_CFG_ROW_MISMATCH pc=%0d cycle=%0d mut=%0d",p,cyc,MUT);', 'if(a_col_v)begin cols=cols+1; if({a_col_we,a_col_bank,a_col_col,a_col_data,a_col_strb} !== {b_col_we,b_col_bank,b_col_col,b_col_data,b_col_strb}) $fatal(1,"PC_CFG_COL_MISMATCH pc=%0d cycle=%0d mut=%0d",p,cyc,MUT);end', 'if(a_row_v && a_row_op==6)refs=refs+1;', 'if(k_v && (!a_k_rdy || a_owner_fault || a_pc_fault)) $fatal(1,"PC_CFG_CALENDAR pc=%0d cycle=%0d",p,cyc);', 'end end endgenerate','always @(posedge clk) if(rst_n) cyc<=cyc+1;', 'initial begin wait(cyc==512); @(negedge clk); if(checks<15000 || cols<32 || refs<32) $fatal(1,"PC_CFG_VACUOUS checks=%0d cols=%0d refs=%0d",checks,cols,refs); $display("PC_CFG_ALL32 PASS checks=%0d writes=%0d refreshes=%0d cycles=512 added_cycles=0",checks,cols,refs); $finish; end endmodule']
Path(sys.argv[1]).write_text('\n'.join(lines)+'\n')
