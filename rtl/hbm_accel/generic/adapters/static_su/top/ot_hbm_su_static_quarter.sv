`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// Static SU QUARTER (H-ELEM-B 2026-10-15): quarter q of the whole SU, placed in quadrant q's VM band beside VM slice q
// (adopted floorplan T_band2__npg4_s5, main 952c5933c; F2 per-quarter spread: quarter q only reads/writes slice q).
//   4 x ot_hbm_su_static_pgslice   port-group slice G = VM bank pair {2G,2G+1} (NPG 4 on every quadrant, BANK_GROUP
//                                  0x33221100): 32 lanes + 32 pinned store banks + 2 SU-station VM leaves + fill/drain;
//   1 x ot_hbm_su_static_qcore     RF replica + reducer between the slices.
// Real hardware only; every operation on compiler-assigned fixed edges (see the slice / core headers for the exact
// edges); no queues, credits, ready, arbitration or replay. Lanes: quarter-local ids 0..127 (quarter 0 lane 0 FULL,
// 0..31 SFU, rest LIGHT) = the full512 arithmetic's quarter (identical per-lane control slice of 1742 bits).
// Command buses per quarter: control[1741:0] (arithmetic broadcast), vmr_cmd/vmw_cmd [8 ports] (port p = VM bank p,
// slice p/2), rf_rd_cmd [6 classes x {v,addr8}], red_cmd {v,op3,a10,b10,dst10,tag32,osel,lane7}.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hbm_su_static_quarter #(
 parameter integer QID=0,READ_RETURN=10,WRITE_RETURN=7,FETCH_EXTRA_EDGES=2,MLAT=3,ALAT=3,LEAF=0,MUT=0,MULTIRATE=0
)(
 input wire [3:0] pg_clk,
 input wire [1023:0] clk_lane, input wire [511:0] clk_insert, input wire [127:0] rst_lane_n,
 input wire [15:0] clk_bcast, rst_bcast_n,
 input wire [127:0] clk_bank,
 input wire [767:0] clk_bank_macro, // per-bank six actual macro roots; register roots remain clk_bank
 input wire [63:0] clk_rf,
 input wire [3:0] clk_ctl,                    // one control/datapath root per slice
 input wire clk_core,clk_red,
 input wire [5:0] clk_side,
 input wire rst_n,
 input wire bridge_rst_n, // phase-zero reset for MULTIRATE boundary only
 input wire [1741:0] control,
 input wire [8*30-1:0] vmr_cmd,
 input wire [8*39-1:0] vmw_cmd,
 input wire [6*9-1:0] rf_rd_cmd,
 input wire [73:0] red_cmd,
 input wire [3:0] rf_wv, input wire [4*8-1:0] rf_wa, input wire [4*32-1:0] rf_wd,
 output wire red_sv, output wire [31:0] red_tag, output wire [31:0] red_x, output wire red_rf_v,
 output wire [8*17-1:0] lg_rq, output wire [8*281-1:0] lg_wq,
 input wire [8*257-1:0] lg_rr, input wire [7:0] lg_w_done,
 output wire [4:0] fault                      // {core, slice 3..0}
);
 wire [4*32-1:0] rf_bword; wire [4*9-1:0] rf_bcmd; wire [255:0] rf_dsec; wire [4*32-1:0] slice_x;
 wire [11:0] red_sel={red_cmd[73],red_cmd[72:70],red_cmd[7],red_cmd[6:0]};
 for(genvar g=0;g<4;g=g+1)begin:g_slice
  ot_hbm_su_static_pgslice #(.QID(QID),.G(g),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),
   .FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.MUT(MUT),.MULTIRATE(MULTIRATE)) u_slice(
   .pg_clk(pg_clk[g]),
   .clk_lane({clk_lane[(64+16*g)*8+:128],clk_lane[(16*g)*8+:128]}),
   .clk_insert({clk_insert[(64+16*g)*4+:64],clk_insert[(16*g)*4+:64]}),
   .rst_lane_n({rst_lane_n[64+16*g+:16],rst_lane_n[16*g+:16]}),
   .clk_bcast(clk_bcast[g*4+:4]),.rst_bcast_n(rst_bcast_n[g*4+:4]),
   .clk_bank({clk_bank[64+16*g+:16],clk_bank[16*g+:16]}),
   .clk_bank_macro({clk_bank_macro[(64+16*g)*6+:96],clk_bank_macro[(16*g)*6+:96]}),
   .clk_ctl(clk_ctl[g]),.clk_side(clk_side),.rst_n(rst_n),.bridge_rst_n(bridge_rst_n),.control(control),
   .vmr_cmd(vmr_cmd[(2*g)*30+:60]),.vmw_cmd(vmw_cmd[(2*g)*39+:78]),
   .rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),.red_sel(red_sel),.slice_x(slice_x[g*32+:32]),
   .lg_rq(lg_rq[(2*g)*17+:34]),.lg_wq(lg_wq[(2*g)*281+:562]),.lg_rr(lg_rr[(2*g)*257+:514]),
   .lg_w_done(lg_w_done[2*g+:2]),.fault(fault[g]));
 end
 ot_hbm_su_static_qcore #(.MUT(MUT)) u_core(.clk_rf(clk_rf),.clk_ctl(clk_core),.clk_red(clk_red),.rst_n(rst_n),
  .rf_rd_cmd(rf_rd_cmd),.red_cmd(red_cmd),.rf_drain_cmd(vmw_cmd[38:37]),.slice_x(slice_x),
  .rf_wv(rf_wv),.rf_wa(rf_wa),.rf_wd(rf_wd),.rf_bword(rf_bword),.rf_bcmd(rf_bcmd),.rf_dsec(rf_dsec),
  .red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.red_rf_v(red_rf_v),.fault(fault[4]));
endmodule
`default_nettype wire
