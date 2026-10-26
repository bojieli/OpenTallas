`timescale 1ns/1ps
// TOKEN-XDIE-S81 bench shim (S81-COLL bank64 safe3, 10-19): the xdie vehicle instantiates dsfd_coll_lane_w/_e by their
// legacy names; this file (passed as LANE= to run_xdie_s81.sh in place of ot_s81ph_coll_lane.sv) binds those names to
// the safe3 tile (ot_s81ph_coll_lane_safe3).  The legacy option parameters are accepted and must match the production
// options safe3 implements (GFMT 1 / EPPIPE 2 / LCR 1).  XDIE_SAFE3_CHB400: the board400 mutant (tile CH_BOARD 400).
`ifdef XDIE_SAFE3_CHB400
`define XDIE_SAFE3_CHB 400
`else
`define XDIE_SAFE3_CHB 700
`endif
module dsfd_coll_lane_w #(parameter integer GFMT = 1, parameter integer EPPIPE = 2, parameter integer LCR = 1,
    parameter integer CH_BOARD = `XDIE_SAFE3_CHB) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    output wire [0:0] tf, input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    initial if (GFMT != 1 || EPPIPE != 2 || LCR != 1) $fatal(1, "safe3 shim: lane options must be GFMT1 EPPIPE2 LCR1");
    ot_s81ph_coll_lane_safe3 #(.CH_BOARD(CH_BOARD)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx), .tf(tf[0]),
        .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
module dsfd_coll_lane_e #(parameter integer GFMT = 1, parameter integer EPPIPE = 2, parameter integer LCR = 1,
    parameter integer CH_BOARD = `XDIE_SAFE3_CHB) (
    input wire [0:0] ck, input wire [0:0] rs, input wire [0:0] chb, input wire [514:0] rx, output wire [511:0] tx,
    output wire [0:0] tf, input wire [0:0] lo_v, output wire [0:0] lo_r, input wire [552:0] lo_d,
    output wire [0:0] li_v, input wire [0:0] li_r, output wire [552:0] li_d, output wire [2:0] flt);
    initial if (GFMT != 1 || EPPIPE != 2 || LCR != 1) $fatal(1, "safe3 shim: lane options must be GFMT1 EPPIPE2 LCR1");
    ot_s81ph_coll_lane_safe3 #(.CH_BOARD(CH_BOARD)) u (.clk(ck[0]), .rs_n(rs[0]), .ch_b(chb[0]), .rx(rx), .tx(tx), .tf(tf[0]),
        .lo_v(lo_v[0]), .lo_r(lo_r[0]), .lo_d(lo_d), .li_v(li_v[0]), .li_r(li_r[0]), .li_d(li_d), .flt(flt));
endmodule
