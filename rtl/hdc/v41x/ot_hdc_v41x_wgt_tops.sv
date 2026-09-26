`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Routed tiles of the V4.1x weight engines (block `wgt`): fixed-parameter
// wrappers of ot_hdc_v41x_wgt_tile, one per physical record under
// results/physical_abi3/asap7/hdc/v41x/.
//
//   ot_hdc_v41x_wgt_qtile     quantised engine, G = 1: one R-ARITH chunk unit of
//                             8 FP8/FP4 block-dot lanes (256 MACs/cycle), its
//                             chain, a 5-level combiner (rows up to 256 blocks,
//                             K = 8192) and the sequencer.  906 per die =
//                             7,248 block-dot lanes = 231,936 MACs/cycle.
//   ot_hdc_v41x_wgt_qtile_m2  the same with the MTP lane multiplier m = 2 (each
//                             weight word feeds 2 block dots): 512 MACs/cycle
//                             on 256 MACs' worth of ROM read.
//   ot_hdc_v41x_wgt_mtile     BF16/FP32 engine, G = 8: 64 MAC lanes (8 chunks),
//                             a 3-level tree, 4 combiners of 7 levels (segments
//                             of 2..8 chunks, rows up to K = 8192), sequencer.
//                             The per-die tile is G = 32 (256 lanes, 123 per
//                             die = 31,488 >= 31,360 MACs/cycle): 4 of these
//                             slices plus two tree levels.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_qtile_g #(
    parameter integer M = 1
) (
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 d_v,
    output wire                 d_rdy,
    input  wire [3:0]           d_plg,
    input  wire [9:0]           d_nb,
    input  wire [15:0]          d_nrows,
    input  wire [19:0]          d_wbase,
    input  wire                 d_ind,
    input  wire [8:0]           d_eid,
    input  wire [19:0]          d_estride,
    input  wire                 d_fp4,
    input  wire [3:0]           d_tag,
    output wire [7:0]           rq_v,
    output wire [8*20-1:0]      rq_a,
    output wire [8*10-1:0]      rq_q,
    output wire [8*4-1:0]       rq_plg,
    output wire [8*4-1:0]       rq_tag,
    input  wire [8*264-1:0]     rd_w,
    input  wire [8*M*264-1:0]   rd_x,
    input  wire                 o_cr,
    output wire                 o_v,
    output wire [15:0]          o_rg,
    output wire [3:0]           o_tag,
    output wire [0:0]           o_mask,
    output wire [M*32-1:0]      o_y,
    output wire [M*16-1:0]      o_bf,
    output wire [M-1:0]         o_f,
    output wire                 idle
);
    ot_hdc_v41x_wgt_tile #(.KIND(0), .G(1), .M(M), .LB(5), .PMIN_LG(0), .AW(20), .NBW(10), .RWW(16), .EIW(9),
                           .TGW(4), .RL(2), .OCRED(128)) u_t (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rd_w(rd_w), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .idle(idle));
endmodule

module ot_hdc_v41x_wgt_qtile (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               d_v,
    output wire               d_rdy,
    input  wire [3:0]         d_plg,
    input  wire [9:0]         d_nb,
    input  wire [15:0]        d_nrows,
    input  wire [19:0]        d_wbase,
    input  wire               d_ind,
    input  wire [8:0]         d_eid,
    input  wire [19:0]        d_estride,
    input  wire               d_fp4,
    input  wire [3:0]         d_tag,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*10-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    input  wire [8*264-1:0]   rd_w,
    input  wire [8*264-1:0]   rd_x,
    input  wire               o_cr,
    output wire               o_v,
    output wire [15:0]        o_rg,
    output wire [3:0]         o_tag,
    output wire [0:0]         o_mask,
    output wire [31:0]        o_y,
    output wire [15:0]        o_bf,
    output wire [0:0]         o_f,
    output wire               idle
);
    ot_hdc_v41x_wgt_qtile_g #(.M(1)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rd_w(rd_w), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .idle(idle));
endmodule

module ot_hdc_v41x_wgt_qtile_m2 (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               d_v,
    output wire               d_rdy,
    input  wire [3:0]         d_plg,
    input  wire [9:0]         d_nb,
    input  wire [15:0]        d_nrows,
    input  wire [19:0]        d_wbase,
    input  wire               d_ind,
    input  wire [8:0]         d_eid,
    input  wire [19:0]        d_estride,
    input  wire               d_fp4,
    input  wire [3:0]         d_tag,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*10-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    input  wire [8*264-1:0]   rd_w,
    input  wire [8*2*264-1:0] rd_x,
    input  wire               o_cr,
    output wire               o_v,
    output wire [15:0]        o_rg,
    output wire [3:0]         o_tag,
    output wire [0:0]         o_mask,
    output wire [63:0]        o_y,
    output wire [31:0]        o_bf,
    output wire [1:0]         o_f,
    output wire               idle
);
    ot_hdc_v41x_wgt_qtile_g #(.M(2)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rd_w(rd_w), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .idle(idle));
endmodule

module ot_hdc_v41x_wgt_mtile (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               d_v,
    output wire               d_rdy,
    input  wire [3:0]         d_plg,
    input  wire [13:0]        d_nb,
    input  wire [15:0]        d_nrows,
    input  wire [19:0]        d_wbase,
    input  wire               d_ind,
    input  wire [8:0]         d_eid,
    input  wire [19:0]        d_estride,
    input  wire               d_fp4,
    input  wire [3:0]         d_tag,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*14-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    input  wire [64*32-1:0]   rd_w,
    input  wire [64*16-1:0]   rd_x,
    input  wire               o_cr,
    output wire               o_v,
    output wire [15:0]        o_rg,
    output wire [3:0]         o_tag,
    output wire [3:0]         o_mask,
    output wire [4*32-1:0]    o_y,
    output wire [4*16-1:0]    o_bf,
    output wire [3:0]         o_f,
    output wire               idle
);
    ot_hdc_v41x_wgt_tile #(.KIND(1), .G(8), .M(1), .LB(7), .PMIN_LG(1), .AW(20), .NBW(14), .RWW(16), .EIW(9),
                           .TGW(4), .RL(2), .OCRED(128)) u_t (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rd_w(rd_w), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .idle(idle));
endmodule
