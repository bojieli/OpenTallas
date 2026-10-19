#!/usr/bin/env python3
"""HBM-TIE 2026-10-17: bench of the refresh_reload producer ot_hbm_pc_refresh_cfg feeding the die PC master.

Miter, 32 PCs of one stack, cycle by cycle on the HBM clock:
  a_<p> = ot_hbm_svc_pc_ctrl_leaf_cfg_h9b with refresh_reload = the run6 die strap (RELOAD formula of
          full_die_v16._pc_refresh_reload), reset = the producer's pc_rst_n (same release edge),
  b_<p> = the same master with refresh_reload = the producer's byte p (loaded by an F20 operand-row frame).
Every output (K ready/response, PHY row/column commands incl. REFpb, faults) must be identical for 4,000 HBM
edges with periodic K writes, and >= 32 refreshes must be seen. Separate producer instances check the refusals:
an out-of-range row (fault, never released) and a second row after a load (fault, bytes unchanged).
The stream (F20) clock and the HBM clock are unrelated periods (0.833 ns / 1.0 ns).
"""
from pathlib import Path
import sys

NPC = 32


def reload(p):
    rp = (p * 118 // 32) % 118
    return 118 + rp + ((rp + 118 + p) % 2)


ROW = sum(reload(p) << (8 * p) for p in range(NPC))
BAD = (ROW & ~(0xff << 8 * 7)) | (50 << 8 * 7)          # PC 7 byte below RMIN
ROW2 = sum(((reload(p) + 1) if reload(p) < 236 else 118) << (8 * p) for p in range(NPC))
inputs = {'k_v': 1, 'k_we': 1, 'k_addr': 30, 'k_len': 4, 'k_tag': 17, 'k_wdata': 256, 'k_wstrb': 32, 'kr_rdy': 1,
          'dram_rvalid': 1, 'dram_rdata': 256}
outputs = {'k_rdy': 1, 'kr_v': 1, 'kr_tag': 17, 'kr_beat': 4, 'kr_data': 256, 'k_wr_done': 1, 'row_v': 1, 'row_op': 3,
           'row_bank': 5, 'row_row': 19, 'col_v': 1, 'col_we': 1, 'col_bank': 5, 'col_col': 5, 'col_data': 256,
           'col_strb': 32, 'pc_fault': 1}
L = ['`timescale 1ns/1ps', 'module tb; parameter MUT=0;',
     'reg clk=0; always #0.4165 clk=~clk; reg hclk=0; always #0.5 hclk=~hclk;',
     'reg rst_n=0, hrst_n=0; integer cyc=0; integer checks=0, cols=0, refs=0;',
     'reg cfg_v=0; reg [7:0] cfg_target=0; reg [11:0] cfg_addr=0; reg [255:0] cfg_data=0;',
     f"localparam [255:0] ROW=256'h{ROW:064x}, BAD=256'h{BAD:064x}, ROW2=256'h{ROW2:064x};",
     'task automatic frame(input [7:0] t, input [11:0] a, input [255:0] d); begin',
     '  @(negedge clk); cfg_v=1; cfg_target=t; cfg_addr=a; cfg_data=d; @(negedge clk); cfg_v=0; repeat(3) @(negedge clk); end endtask',
     'wire [255:0] rr_m, rr_bad, rr_rw; wire prst_m, prst_bad, prst_rw; wire rdy_m, act_m, flt_m, rdy_bad, act_bad, flt_bad, rdy_rw, act_rw, flt_rw;',
     f'ot_hbm_pc_refresh_cfg #(.NPC({NPC}),.MUT((MUT==2||MUT==4)?MUT:0)) prod_m(.clk(clk),.rst_n(rst_n),.clk_hbm(hclk),.rst_hbm_n(hrst_n),.tgt(8\'d126),'
     '.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.refresh_reload(rr_m),.pc_rst_n(prst_m),'
     '.ready(rdy_m),.active(act_m),.fault(flt_m));',
     f'ot_hbm_pc_refresh_cfg #(.NPC({NPC}),.MUT((MUT==1)?1:0)) prod_bad(.clk(clk),.rst_n(rst_n),.clk_hbm(hclk),.rst_hbm_n(hrst_n),.tgt(8\'d127),'
     '.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.refresh_reload(rr_bad),.pc_rst_n(prst_bad),'
     '.ready(rdy_bad),.active(act_bad),.fault(flt_bad));',
     f'ot_hbm_pc_refresh_cfg #(.NPC({NPC}),.MUT((MUT==3)?3:0)) prod_rw(.clk(clk),.rst_n(rst_n),.clk_hbm(hclk),.rst_hbm_n(hrst_n),.tgt(8\'d125),'
     '.cfg_v(cfg_v),.cfg_target(cfg_target),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.refresh_reload(rr_rw),.pc_rst_n(prst_rw),'
     '.ready(rdy_rw),.active(act_rw),.fault(flt_rw));',
     # host boot sequence: late first frame so an early release is visible
     'initial begin repeat(4) @(negedge clk); rst_n=1; hrst_n=1; repeat(150) @(negedge clk);',
     "  frame(8'd127, 12'h800, BAD); frame(8'd125, 12'h800, ROW); frame(8'd125, 12'h800, ROW2); frame(8'd126, 12'h800, ROW);",
     'end',
     'always @(posedge hclk) if(hrst_n) cyc<=cyc+1;',
     # release discipline and refusals
     'always @(negedge hclk) if(hrst_n) begin',
     '  if(prst_m && rr_m!==ROW) $fatal(1,"PC_REFCFG_RELEASED_WITHOUT_ROW cycle=%0d mut=%0d",cyc,MUT);',
     '  if(prst_bad) $fatal(1,"PC_REFCFG_BAD_ROW_RELEASED cycle=%0d mut=%0d",cyc,MUT);',
     '  if(prst_rw && rr_rw!==ROW) $fatal(1,"PC_REFCFG_REWRITE_ACCEPTED cycle=%0d mut=%0d",cyc,MUT);',
     'end',
     'genvar p; generate for(p=0;p<32;p=p+1) begin:g',
     'localparam integer RP=(p*118/32)%118; localparam integer RELOAD=118+RP+((RP+118+p)%2);']
for n, w in inputs.items():
    expr = {'k_v': 'prst_m && cyc>=600 && cyc<3900 && ((cyc-600)%512==0)', 'k_we': "1'b1", 'k_addr': "30'(p*4)",
            'k_len': "4'd1", 'k_tag': "17'(cyc)", 'k_wdata': "{8{32'(32'h12340000+p+cyc)}}", 'k_wstrb': "32'hffffffff",
            'kr_rdy': "1'b1", 'dram_rvalid': "1'b0", 'dram_rdata': "256'b0"}[n]
    L.append(f'wire [{w-1}:0] {n}={expr};')
for n, w in outputs.items():
    L.append(f'wire [{w-1}:0] a_{n},b_{n};')
L.append('wire [5:0] a_of,b_of;')
for pre, rr in [('a', "8'(RELOAD)"), ('b', 'rr_m[p*8+:8]')]:
    con = ['.clk(hclk)', '.rst_n(prst_m)', ".pc_id(5'(p))", f'.refresh_reload({rr})'] + [f'.{n}({n})' for n in inputs] + \
          [f'.{n}({pre}_{n})' for n in outputs] + [f'.owner_fault_split({pre}_of)']
    L.append(f'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b {pre}(' + ','.join(con) + ');')
comp = ['k_rdy', 'kr_v', 'k_wr_done', 'row_v', 'col_v', 'pc_fault']
L += ['always @(negedge hclk) if(prst_m) begin', 'checks=checks+1;',
      "if({" + ','.join('a_' + n for n in comp) + ',a_of} !== {' + ','.join('b_' + n for n in comp) +
      ',b_of}) $fatal(1,"PC_REFCFG_MISMATCH pc=%0d cycle=%0d mut=%0d",p,cyc,MUT);',
      'if(a_row_v && {a_row_op,a_row_bank,a_row_row} !== {b_row_op,b_row_bank,b_row_row}) $fatal(1,"PC_REFCFG_ROW_MISMATCH pc=%0d cycle=%0d mut=%0d",p,cyc,MUT);',
      'if(a_col_v)begin cols=cols+1; if({a_col_we,a_col_bank,a_col_col,a_col_data,a_col_strb} !== {b_col_we,b_col_bank,b_col_col,b_col_data,b_col_strb}) $fatal(1,"PC_REFCFG_COL_MISMATCH pc=%0d cycle=%0d mut=%0d",p,cyc,MUT);end',
      'if(a_row_v && a_row_op==6)refs=refs+1;',
      'if(a_pc_fault || (|a_of)) $fatal(1,"PC_REFCFG_CONTROLLER_FAULT pc=%0d cycle=%0d",p,cyc);',
      'end end endgenerate',
      'initial begin wait(cyc==4000); @(negedge hclk);',
      '  if(!rdy_m || flt_m || act_m || !prst_m) $fatal(1,"PC_REFCFG_STATUS main rdy=%0d flt=%0d act=%0d rel=%0d mut=%0d",rdy_m,flt_m,act_m,prst_m,MUT);',
      '  if(!flt_bad || rdy_bad) $fatal(1,"PC_REFCFG_BAD_ROW_NOT_REFUSED mut=%0d",MUT);',
      '  if(!flt_rw || rr_rw!==ROW) $fatal(1,"PC_REFCFG_REWRITE_NOT_REFUSED mut=%0d",MUT);',
      '  if(checks<32*3000 || cols<32*6 || refs<32*20) $fatal(1,"PC_REFCFG_VACUOUS checks=%0d cols=%0d refs=%0d",checks,cols,refs);',
      '  $display("PC_REFCFG PASS pcs=32 checks=%0d writes=%0d refreshes=%0d hbm_cycles=4000 boot_frames=4",checks,cols,refs);',
      '  $finish; end endmodule']
Path(sys.argv[1]).write_text('\n'.join(L) + '\n')
