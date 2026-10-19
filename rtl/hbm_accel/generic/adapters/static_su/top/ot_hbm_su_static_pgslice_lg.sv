`timescale 1ns/1ps
`default_nettype none
// SU bank-group slice WITH its two LG taps folded in (coordinator 0db 10-17: lg_static_bank folds into its consumer
// tile; no separate tap slots). = unchanged ot_hbm_su_static_pgslice + ot_hbm_vm_lg_pair_tap (SU level, return
// edges READ_RETURN/WRITE_RETURN = the slice's own 10/7, no rret/wret straps). Ports: every pgslice port unchanged
// except lg_* which now face the VM bank (= the taps' near side); new lg_read/lg_write (calendar local selects),
// far_rq/far_wq (from the SFU-level taps) and far_rr/far_w_done (to them); lg_fault = OR of the two taps.
// The taps run on pg_clk (the slice's VM bank leaf clock). Generated from the pgslice port list (one-off; static).
// RSYNC (HBM-SU3 2026-10-17, default 1): the serial power-on reset rst_n reaches the stream-domain taps and the
// slice's two VM bank leaves through 1-bit serial->stream synchronisers (clk_ctl source flop + two pg_clk flops): the
// taps in the hardened leaf ot_hbm_su_static_pg_lg_tap, the leaves by pgslice PG_RSYNC=1. RSYNC=0 = the r8b structure
// (one pg_clk flop of rst_n for the taps, raw async rst_n on the leaves), kept only as the bench reference.
// Datapath edges unchanged; reset assert/release on the stream side move to the synchronised edges.
// STRAP (OWN-PGLG 2026-10-18, default 0): pgslice STRAP -- {QID,G} from the position strap pos = {qid, g}; QID/G
// parameters then only pick the structure class (LIGHT G2/3, HEAVY G0/1, Q0G0), so 16 slices are 3 masters.
module ot_hbm_su_static_pgslice_lg #(
 parameter integer QID=0,G=0,READ_RETURN=10,WRITE_RETURN=7,FETCH_EXTRA_EDGES=2,MLAT=3,ALAT=3,LEAF=0,MUT=0,MULTIRATE=0,
 parameter integer PIN_REG=0,
 parameter integer COLLPORT=0,
 parameter integer B39_NOOP=(QID==0),
 parameter integer RF_LOCAL=0,
 parameter integer RSYNC=1,
 parameter integer RSYNC_MUT=0,
 parameter integer STRAP=0,
 // PRETREE (HH-6 / TW-HBM-PGLG 10-19, default 0): pgslice PRETREE pass-through (tree_cmd in, tree_o out)
 parameter integer PRETREE=0
)(
 input wire pg_clk,
 input wire [255:0] clk_lane,
 input wire [127:0] clk_insert,
 input wire [31:0] rst_lane_n,
 input wire [3:0] clk_bcast,
 input wire [3:0] rst_bcast_n,
 input wire [31:0] clk_bank,
 input wire [191:0] clk_bank_macro,
 input wire clk_ctl,
 input wire [5:0] clk_side,
 input wire rst_n,
 input wire [3:0] pos,
 input wire bridge_rst_n,
 input wire [1741:0] control,
 input wire [2*30-1:0] vmr_cmd,
 input wire [2*39-1:0] vmw_cmd,
 input wire [4*32-1:0] rf_bword,
 input wire [4*9-1:0] rf_bcmd,
 input wire [255:0] rf_dsec,
 input wire [11:0] red_sel,
 output wire [31:0] slice_x,
 input wire [11:0] tree_cmd,
 output wire [66:0] tree_o,
 input wire [1:0] inj_rd,
 input wire [159:0] inj_addr,
 output wire [1023:0] inj_q,
 input wire [1:0] dw_v,
 input wire [17:0] dw_row,
 input wire [1023:0] dw_d,
 output wire fault,
 output wire [33:0] lg_rq,
 output wire [561:0] lg_wq,
 input wire [513:0] lg_rr,
 input wire [1:0] lg_w_done,
 input wire [1:0] lg_read,lg_write,
 input wire [33:0] far_rq,
 input wire [561:0] far_wq,
 output wire [513:0] far_rr,
 output wire [1:0] far_w_done,
 output wire lg_fault
);
 wire [33:0] s_rq; wire [561:0] s_wq; wire [513:0] s_rr; wire [1:0] s_done;
 ot_hbm_su_static_pgslice #(.QID(QID),.G(G),.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.FETCH_EXTRA_EDGES(FETCH_EXTRA_EDGES),.MLAT(MLAT),.ALAT(ALAT),.LEAF(LEAF),.MUT(MUT),.MULTIRATE(MULTIRATE),.PIN_REG(PIN_REG),.COLLPORT(COLLPORT),.B39_NOOP(B39_NOOP),.RF_LOCAL(RF_LOCAL),.PG_RSYNC(RSYNC),.STRAP(STRAP),.PRETREE(PRETREE)) u_slice(
  .pg_clk(pg_clk),
  .clk_lane(clk_lane),
  .clk_insert(clk_insert),
  .rst_lane_n(rst_lane_n),
  .clk_bcast(clk_bcast),
  .rst_bcast_n(rst_bcast_n),
  .clk_bank(clk_bank),
  .clk_bank_macro(clk_bank_macro),
  .clk_ctl(clk_ctl),
  .clk_side(clk_side),
  .rst_n(rst_n),
  .pos(pos),
  .bridge_rst_n(bridge_rst_n),
  .control(control),
  .vmr_cmd(vmr_cmd),
  .vmw_cmd(vmw_cmd),
  .rf_bword(rf_bword),
  .rf_bcmd(rf_bcmd),
  .rf_dsec(rf_dsec),
  .red_sel(red_sel),
  .slice_x(slice_x),
  .tree_cmd(tree_cmd),
  .tree_o(tree_o),
  .lg_rq(s_rq),
  .lg_wq(s_wq),
  .lg_rr(s_rr),
  .lg_w_done(s_done),
  .inj_rd(inj_rd),
  .inj_addr(inj_addr),
  .inj_q(inj_q),
  .dw_v(dw_v),
  .dw_row(dw_row),
  .dw_d(dw_d),
  .fault(fault));
 if(RSYNC)begin:g_tap
  ot_hbm_su_static_pg_lg_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN),.RSYNC_MUT(RSYNC_MUT)) u_tap(
   .clk_ctl(clk_ctl),.pg_clk(pg_clk),.rst_n(rst_n),.local_rq(s_rq),.far_rq(far_rq),.local_wq(s_wq),.far_wq(far_wq),
   .local_read(lg_read),.local_write(lg_write),.near_rq(lg_rq),.near_wq(lg_wq),.near_rr(lg_rr),.near_w_done(lg_w_done),
   .local_rr(s_rr),.far_rr(far_rr),.local_w_done(s_done),.far_w_done(far_w_done),.fault(lg_fault));
 end else begin:g_tap_r8b
  (* keep = "true" *) reg lg_rst; always @(posedge pg_clk) lg_rst <= rst_n;
  ot_hbm_vm_lg_pair_tap #(.READ_RETURN(READ_RETURN),.WRITE_RETURN(WRITE_RETURN)) u_tap(
   .clk(pg_clk),.rst_n(lg_rst),.local_rq(s_rq),.far_rq(far_rq),.local_wq(s_wq),.far_wq(far_wq),
   .local_read(lg_read),.local_write(lg_write),.near_rq(lg_rq),.near_wq(lg_wq),.near_rr(lg_rr),.near_w_done(lg_w_done),
   .local_rr(s_rr),.far_rr(far_rr),.local_w_done(s_done),.far_w_done(far_w_done),.fault(lg_fault));
 end
endmodule
`default_nettype wire
