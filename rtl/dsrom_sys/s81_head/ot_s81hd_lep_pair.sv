`timescale 1ns/1ps
`default_nettype none
// DIE-HEAD-9 LEP split (COORD 2026-10-28 06:30 ruling (4)): one PEER PAIR child
// of hd_lep0N = the existing g_lane[k] body of ot_s81hd_lep0N_core, unchanged:
// the K-side MU lane landing ot_s81_mu72_lnland_nst plus the safe8 collective
// lane dsfd_coll_lane_w_safe8_ntf, with their private n_* link (credit, data,
// rxv, flt) kept INSIDE the child.  Wrapper only: same instances, parameters
// and nets; 0 added cycles.  Selected by ot_s81hd_lep0N_core PAIR=1 (default 0
// keeps the original flat g_lane hierarchy).  Child faces: K side = k_* (to
// u_lep), collective side = coll_i/coll_o (the die collective pins).
module ot_s81hd_lep_pair #(parameter [0:0] CHB=1'b1)(
 input  wire clk,rst_n,
 input  wire k_lo_v,output wire k_lo_r,input wire[552:0]k_lo_d,
 output wire k_li_v,input  wire k_li_r,output wire[552:0]k_li_d,
 input  wire k_rxv,output wire[2:0]k_flt,
 input  wire[513:0]coll_i,output wire[511:0]coll_o
);
 wire lv,lr,liv,lir,lrx;wire[552:0]ld,lid;wire[2:0]lf;
 ot_s81_mu72_lnland_nst #(.MUT(0))u_land(
  .ck_k(clk),.ck_n(clk),.rs_k(rst_n),.rs_n(rst_n),
  .k_lo_v(k_lo_v),.k_lo_r(k_lo_r),.k_lo_d(k_lo_d),
  .k_li_v(k_li_v),.k_li_r(k_li_r),.k_li_d(k_li_d),
  .k_rxv(k_rxv),.k_flt(k_flt),
  .n_lo_v(lv),.n_lo_r(lr),.n_lo_d(ld),
  .n_li_v(liv),.n_li_r(lir),.n_li_d(lid),
  .n_rxv(lrx),.n_flt(lf));
 dsfd_coll_lane_w_safe8_ntf #(.CORE_CRED(12))u_lane(
  .ck(clk),.rs(rst_n),.chb(CHB),
  .rx({coll_i[512],coll_i[513],coll_i[511:0],lrx}),
  .tx(coll_o),.lo_v(lv),.lo_r(lr),.lo_d(ld),
  .li_v(liv),.li_r(lir),.li_d(lid),.flt(lf));
endmodule
`default_nettype wire
