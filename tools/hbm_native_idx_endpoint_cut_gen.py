#!/usr/bin/env python3
"""Source exact named clock successors; all physical boundaries unqualified."""
import re
from pathlib import Path
out=Path('rtl/hbm_accel/index')
s=Path(out/'ot_hbm_idx_score_owned_native.sv').read_text().replace('module ot_hbm_idx_score_owned_native #','module ot_hbm_idx_score_cut_native #',1)
s=s.replace('input wire [NS-1:0] clk_engine,clk_meta,clk_tail,','input wire [NP-1:0] clk_line,\n  input wire [NP*3-1:0] clk_line_mem,\n  input wire [NS-1:0] clk_engine,clk_meta,clk_tail,',1)
s=s.replace('wire [NP-1:0] lne;','wire [NP-1:0] lne;\n  wire [NP-1:0] line_fault;',1)
a=s.index('    end else begin : cc');b=s.index('    end\n  end endgenerate',a)
part=s[a:b].replace('posedge ck','posedge clk_line[p]').replace('hfd_idx_fifo #(.W(1098), .AW(FA)) u_f (.ck(ck),','ot_hbm_idx_landing_fifo_native #(.W(1098), .AW(FA)) u_f (.clk(clk_line[p]), .clk_mem(clk_line_mem[p*3+:3]),').replace('.rd(lrd[p*1098 +: 1098]), .ne(lne[p]), .cnt(cnt_));','.rd(lrd[p*1098 +: 1098]), .ne(lne[p]), .cnt(cnt_), .fault(line_fault[p]));')
s=s[:a]+part+s[b:]
s=s.replace('if (FWD) begin : fw','if (FWD) begin : fw\n      assign line_fault[p]=1\'b0;',1).replace('if (pfault) fault <= 1\'b1;','if (pfault || |line_fault) fault <= 1\'b1;',1)
(out/'ot_hbm_idx_score_cut_native.sv').write_text(s)
s=Path('physical/hbm_accel_die_views/index/rtl/hfd_idx_sel.sv').read_text().replace('module hfd_idx_sel #','module ot_hbm_idx_selector_cut_native #',1)
s=s.replace('input  wire          ck,','input wire ck,clk_query,clk_quant,clk_quant_delay,\n  input wire [3:0] clk_query_bank,\n  input wire clk_top,clk_top_ctl,\n  input wire [3:0] clk_top_slice,\n  input wire [7:0] clk_top_hist,clk_top_pack,\n  input wire [1:0] clk_top_search,\n  input wire [3:0] clk_score_fifo,\n  input wire [11:0] clk_score_mem,clk_top_mem,',1)
s=s.replace('ot_hbm_accel_index_query #(.ENABLE(1)) u_index_q (\n    .clk(ck),','ot_hbm_idx_query_owned_native u_index_q (\n    .clk(clk_query), .clk_quant(clk_quant), .clk_quant_delay(clk_quant_delay), .clk_bank(clk_query_bank),',1)
# TopK-only native collector handles candidates outside this selector.
a=s.index('  // ------------------------------------------------------------------ layer-20 candidates');b=s.index('  //',a+20) if False else s.index('  // ------------------------------------------------------------------',a+80)
# Keep candidate signal declarations used by final output sequencer, remove actual unused heap+memory.
p=s.index('  ot_hbm_accel_index_candidate',a);end=s.index('  end endgenerate',p)+len('  end endgenerate')
s=s[:p]+'''  assign cand_ready=4'b1111;
  assign c_v=0;assign c_last=0;assign c_lv=0;assign c_val=0;assign c_blk=0;
  assign crep=0;assign covf=0;assign cand_busy=0;assign cand_stats=0;
''' +s[end:]
s=s.replace('ot_hdc_v41x_sel #(.Q(Q)', 'ot_hbm_idx_sel_owned_native #(.Q(Q)',1)
a=s.index('  ot_hbm_idx_sel_owned_native');b=s.index('  generate for (gq',a)
s=s[:a]+s[a:b].replace('.clk(ck),','.clk(clk_top), .clk_ctl(clk_top_ctl), .clk_slice(clk_top_slice), .clk_hist(clk_top_hist), .clk_pack(clk_top_pack), .clk_search(clk_top_search),',1)+s[b:]
# SRAM landing explicit per-queue control+three memory clock entries, exactly128credits.
s=s.replace('wire [Q*T-1:0] lne;', 'wire [Q*T-1:0] landing_fault;\n  wire [Q*T-1:0] lne;',1)
s=s.replace('wire ovf_unused;', 'wire ovf_unused;\n        assign landing_fault[B]=ovf_unused;\n        wire [LA:0] cnt_;',1)
s=s.replace('end else begin : g_ff','end else begin : g_ff\n        assign landing_fault[B]=0;',1)
s=s.replace('if (qs_fault ||', 'if (qs_fault || |landing_fault ||',1)
s=s.replace('ot_fifo_sram_fwft #(.W(SW-1), .DEPTH(1 << LA), .MACRO(2)) u_l (.clk(ck), .rst_n(rn), .push(siv[B]), .wdata(sid[B]),\n          .pop(pop[B]), .hv(lne[B]), .head(lrd[B]), .ovf(ovf_unused));','ot_hbm_idx_landing_fifo_native #(.W(SW-1), .AW(LA), .MACRO(1)) u_l (.clk(clk_score_fifo[B]), .clk_mem(clk_score_mem[B*3+:3]), .rst_n(rn), .we(siv[B]), .wd(sid[B]),\n          .re(pop[B]), .ne(lne[B]), .rd(lrd[B]), .cnt(cnt_), .fault(ovf_unused));',1)
# TopK memories3macro/quarter, own externally driven memory+capture clock.
s=s.replace('hfd_idx_mem #(.W(W*(17+IW))','ot_hbm_idx_line_memory_owned_native #(.W(W*(17+IW))',1)
s=s.replace('u_m (.ck(ck), .we(m_we[gq])','u_m (.ck(ck), .clk_mem(clk_top_mem[gq*3+:3]), .we(m_we[gq])',1)
# Restrict this source to native fixed profile; other values do not imply qualified hardware.
s=s.replace('  localparam integer Q = 4, W = 16, IW = 20;','  initial if(T!=1 || LA!=7 || MEMV!=1 || READLAT!=2) $fatal(1,"Native selector cut fixed profile only");\n  localparam integer Q = 4, W = 16, IW = 20;',1)
(out/'ot_hbm_idx_selector_cut_native.sv').write_text(s)

lib=Path('physical/hbm_accel_die_views/index/rtl/hfd_idx_lib.sv').read_text()
lib=lib[lib.index('module hfd_idx_mem'):].replace('module hfd_idx_mem #','module ot_hbm_idx_line_memory_owned_native #',1).replace('input wire ck,','input wire ck, input wire [((W+255)/256)-1:0] clk_mem,',1).replace('u (.clk(ck),','u (.clk(clk_mem[i]),')
(out/'ot_hbm_idx_line_memory_owned_native.sv').write_text('// Distinct memory+capture clock interface; no old clock ABI alias.\n'+lib)
