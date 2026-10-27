`timescale 1ns/1ps
`default_nettype none
// ot_hbm_su_static_qcore_r13_w2 (HBM-BIND 2026-10-24): the B2 die (NW + NE quadrants only) SU core.  The as-built core
// ot_hbm_su_static_qcore_r13 has a fixed 4-writer register-file port (rf_wv[3:0] / rf_wa / rf_wd, writer = SU tree leg:
// 0 SW, 1 SE, 2 NW, 3 NE; ot_hbm_su_stree_leaf).  On B2 the tree has two legs (ot_hbm_su_stree_root2, leaf NLEG 2:
// writer 0 = NW reducer, 1 = NE reducer), so this master exposes a 2-writer port and binds it to the core's writers 2 / 3
// -- the same writers, same priority (NE over NW) and same edges as the 4-leg die.  Core writers 0 / 1 have no source on
// B2: they are removed structurally (constant inside this master; synthesis prunes their write-select / data legs), so
// the die carries no tie-off.  Everything else is the unchanged core (same params, ports, latencies).
// MUTW (bench only): 1 binds writer 0 -> core 3, writer 1 -> core 2 (swapped priority).
module ot_hbm_su_static_qcore_r13_w2 #(parameter integer MUT=0,COLLPORT=1,RF_LOCAL=1,PRETREE=0,ROW_EN=0,WDEC=0,MUTW=0)(
 input wire clk_ctl,rst_n,
 input wire [6*9-1:0] rf_rd_cmd,
 input wire [73:0] red_cmd,
 input wire [1:0] rf_drain_cmd,
 input wire [4*32-1:0] slice_x,
 input wire [1:0] rf_wv, input wire [2*8-1:0] rf_wa, input wire [2*32-1:0] rf_wd,
 output wire [4*32-1:0] rf_bword,
 output wire [4*9-1:0] rf_bcmd,
 output wire [255:0] rf_dsec,
 output wire red_sv, output wire [31:0] red_tag, output wire [31:0] red_x,
 output wire red_rf_v,
 input wire rr_wv,
 input wire [4:0] rr_wa,
 input wire [255:0] rr_wd,
 input wire [31:0] sfu_x,
 input wire [4*67-1:0] slice_t,
 output wire fault
);
 wire [3:0] wv = (MUTW == 1) ? {rf_wv[0], rf_wv[1], 2'b00} : {rf_wv, 2'b00};
 wire [31:0] wa = (MUTW == 1) ? {rf_wa[7:0], rf_wa[15:8], 16'd0} : {rf_wa, 16'd0};
 wire [127:0] wd = (MUTW == 1) ? {rf_wd[31:0], rf_wd[63:32], 64'd0} : {rf_wd, 64'd0};
 ot_hbm_su_static_qcore_r13 #(.MUT(MUT),.COLLPORT(COLLPORT),.RF_LOCAL(RF_LOCAL),.PRETREE(PRETREE),.ROW_EN(ROW_EN),.WDEC(WDEC)) u_core(
  .clk_ctl(clk_ctl),.rst_n(rst_n),.rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),.rf_drain_cmd(rf_drain_cmd),.slice_x(slice_x),
  .rf_wv(wv),.rf_wa(wa),.rf_wd(wd),.rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),
  .red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.red_rf_v(red_rf_v),.rr_wv(rr_wv),.rr_wa(rr_wa),.rr_wd(rr_wd),
  .sfu_x(sfu_x),.slice_t(slice_t),.fault(fault));
endmodule
`default_nettype wire
