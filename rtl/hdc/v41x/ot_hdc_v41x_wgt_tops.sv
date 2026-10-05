`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// Routed tiles of the V4.1x weight engines (block `wgt`): fixed-parameter
// wrappers of ot_hdc_v41x_wgt_tile, one per physical record under
// results/physical_abi3/asap7/hdc/v41x/.
//
//   ot_hdc_v41x_wgt_qtile       quantised engine, G = 1: one R-ARITH chunk unit
//                               of 8 FP8/FP4 block-dot lanes (256 MACs/cycle),
//                               its chain, a 5-level combiner (rows up to 256
//                               blocks, K = 8192) and the sequencer.
//   ot_hdc_v41x_wgt_qtile_m2    the same with the MTP lane multiplier m = 2.
//   ot_hdc_v41x_wgt_qtile_pool  R-U2 pooled block-dot tile (POOL = 1): + the
//                               stream operand port (HBM index keys), the split
//                               chain (two 4-block index rows per chunk unit),
//                               per-mode activation counters.
//   ot_hdc_v41x_wgt_mtile       BF16/FP32 engine, G = 8: 64 MAC lanes (8 chunks),
//                               a 3-level tree, 4 combiners of 7 levels,
//                               sequencer; per-word operand format (BF16/FP32,
//                               FP8 + UE8M0).  The per-die tile is G = 32 (256
//                               lanes): 4 of these slices plus two tree levels.
//   ot_hdc_v41x_wgt_mtile_pool  R-U2 pooled BF16 tile (POOL = 1): + the stream
//                               operand port (KV row staging) and the FP4 E2M1 x
//                               E4M3-scale operand format (compressed KV rows),
//                               per-mode activation counters.
// The unused ports of a non-pooled tile (d_src, d_split, rd_k, the split outputs)
// are tied off here.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_wgt_qtop #(
    parameter integer M = 1,
    parameter integer POOL = 0
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
    input  wire                 d_src,
    input  wire                 d_split,
    output wire [7:0]           rq_v,
    output wire [8*20-1:0]      rq_a,
    output wire [8*10-1:0]      rq_q,
    output wire [8*4-1:0]       rq_plg,
    output wire [8*4-1:0]       rq_tag,
    output wire [7:0]           rq_src,
    output wire [7:0]           rq_split,
    output wire [8*16-1:0]      rq_rg,
    input  wire [8*264-1:0]     rd_w,
    input  wire [8*264-1:0]     rd_k,
    input  wire [8*M*264-1:0]   rd_x,
    input  wire                 o_cr,
    output wire                 o_v,
    output wire [15:0]          o_rg,
    output wire [3:0]           o_tag,
    output wire [0:0]           o_mask,
    output wire [M*32-1:0]      o_y,
    output wire [M*16-1:0]      o_bf,
    output wire [M-1:0]         o_f,
    output wire [0:0]           o_smask,
    output wire [M*32-1:0]      o_ys,
    output wire [M*16-1:0]      o_bfs,
    output wire [M-1:0]         o_fs,
    output wire [31:0]          o_cnt_rom,
    output wire [31:0]          o_cnt_stream,
    output wire [31:0]          o_cnt_split,
    output wire                 idle
);
    ot_hdc_v41x_wgt_tile #(.KIND(0), .G(1), .M(M), .LB(5), .PMIN_LG(0), .AW(20), .NBW(10), .RWW(16), .EIW(9),
                           .TGW(4), .RL(2), .OCRED(128), .POOL(POOL)) u_t (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .d_src(d_src), .d_split(d_split),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(rq_src),
        .rq_split(rq_split), .rq_rg(rq_rg), .rd_w(rd_w), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(o_smask), .o_ys(o_ys), .o_bfs(o_bfs), .o_fs(o_fs), .o_cnt_rom(o_cnt_rom),
        .o_cnt_stream(o_cnt_stream), .o_cnt_split(o_cnt_split), .idle(idle));
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
    wire [7:0] u_src, u_spl;
    wire [8*16-1:0] u_rg;
    wire [0:0] u_sm, u_fs;
    wire [31:0] u_ys, u_c0, u_c1, u_c2;
    wire [15:0] u_bfs;
    ot_hdc_v41x_wgt_qtop #(.M(1), .POOL(0)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .d_src(1'b0), .d_split(1'b0),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(u_src), .rq_split(u_spl),
        .rq_rg(u_rg), .rd_w(rd_w), .rd_k({(8*264){1'b0}}), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(u_sm), .o_ys(u_ys), .o_bfs(u_bfs), .o_fs(u_fs), .o_cnt_rom(u_c0), .o_cnt_stream(u_c1),
        .o_cnt_split(u_c2), .idle(idle));
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
    wire [7:0] u_src, u_spl;
    wire [8*16-1:0] u_rg;
    wire [0:0] u_sm;
    wire [1:0] u_fs;
    wire [63:0] u_ys;
    wire [31:0] u_bfs, u_c0, u_c1, u_c2;
    ot_hdc_v41x_wgt_qtop #(.M(2), .POOL(0)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .d_src(1'b0), .d_split(1'b0),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(u_src), .rq_split(u_spl),
        .rq_rg(u_rg), .rd_w(rd_w), .rd_k({(8*264){1'b0}}), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(u_sm), .o_ys(u_ys), .o_bfs(u_bfs), .o_fs(u_fs), .o_cnt_rom(u_c0), .o_cnt_stream(u_c1),
        .o_cnt_split(u_c2), .idle(idle));
endmodule

module ot_hdc_v41x_wgt_qtile_pool (
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
    input  wire               d_src,
    input  wire               d_split,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*10-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    output wire [7:0]         rq_src,
    output wire [7:0]         rq_split,
    output wire [8*16-1:0]    rq_rg,
    input  wire [8*264-1:0]   rd_w,
    input  wire [8*264-1:0]   rd_k,
    input  wire [8*264-1:0]   rd_x,
    input  wire               o_cr,
    output wire               o_v,
    output wire [15:0]        o_rg,
    output wire [3:0]         o_tag,
    output wire [0:0]         o_mask,
    output wire [31:0]        o_y,
    output wire [15:0]        o_bf,
    output wire [0:0]         o_f,
    output wire [0:0]         o_smask,
    output wire [31:0]        o_ys,
    output wire [15:0]        o_bfs,
    output wire [0:0]         o_fs,
    output wire [31:0]        o_cnt_rom,
    output wire [31:0]        o_cnt_stream,
    output wire [31:0]        o_cnt_split,
    output wire               idle
);
    ot_hdc_v41x_wgt_qtop #(.M(1), .POOL(1)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(d_fp4), .d_tag(d_tag),
        .d_src(d_src), .d_split(d_split),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(rq_src),
        .rq_split(rq_split), .rq_rg(rq_rg), .rd_w(rd_w), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(o_smask), .o_ys(o_ys), .o_bfs(o_bfs), .o_fs(o_fs), .o_cnt_rom(o_cnt_rom),
        .o_cnt_stream(o_cnt_stream), .o_cnt_split(o_cnt_split), .idle(idle));
endmodule

module ot_hdc_v41x_wgt_mtop #(
    parameter integer POOL = 0
) (
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
    input  wire [3:0]         d_tag,
    input  wire               d_src,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*14-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    output wire [7:0]         rq_src,
    output wire [8*16-1:0]    rq_rg,
    input  wire [64*34-1:0]   rd_w,
    input  wire [64*34-1:0]   rd_k,
    input  wire [64*16-1:0]   rd_x,
    input  wire               o_cr,
    output wire               o_v,
    output wire [15:0]        o_rg,
    output wire [3:0]         o_tag,
    output wire [3:0]         o_mask,
    output wire [4*32-1:0]    o_y,
    output wire [4*16-1:0]    o_bf,
    output wire [3:0]         o_f,
    output wire [31:0]        o_cnt_rom,
    output wire [31:0]        o_cnt_stream,
    output wire               idle
);
    wire [7:0] u_spl;
    wire [7:0] u_sm, u_fs;
    wire [8*32-1:0] u_ys;
    wire [8*16-1:0] u_bfs;
    wire [31:0] u_c2;
    ot_hdc_v41x_wgt_tile #(.KIND(1), .G(8), .M(1), .LB(7), .PMIN_LG(1), .AW(20), .NBW(14), .RWW(16), .EIW(9),
                           .TGW(4), .RL(2), .OCRED(128), .POOL(POOL)) u_t (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_fp4(1'b0), .d_tag(d_tag),
        .d_src(d_src), .d_split(1'b0),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(rq_src),
        .rq_split(u_spl), .rq_rg(rq_rg), .rd_w(rd_w), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_smask(u_sm), .o_ys(u_ys), .o_bfs(u_bfs), .o_fs(u_fs), .o_cnt_rom(o_cnt_rom),
        .o_cnt_stream(o_cnt_stream), .o_cnt_split(u_c2), .idle(idle));
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
    input  wire [3:0]         d_tag,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*14-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    input  wire [64*34-1:0]   rd_w,
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
    wire [7:0] u_src;
    wire [8*16-1:0] u_rg;
    wire [31:0] u_c0, u_c1;
    ot_hdc_v41x_wgt_mtop #(.POOL(0)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_tag(d_tag), .d_src(1'b0),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(u_src), .rq_rg(u_rg),
        .rd_w(rd_w), .rd_k({(64*34){1'b0}}), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_cnt_rom(u_c0), .o_cnt_stream(u_c1), .idle(idle));
endmodule

module ot_hdc_v41x_wgt_mtile_pool (
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
    input  wire [3:0]         d_tag,
    input  wire               d_src,
    output wire [7:0]         rq_v,
    output wire [8*20-1:0]    rq_a,
    output wire [8*14-1:0]    rq_q,
    output wire [8*4-1:0]     rq_plg,
    output wire [8*4-1:0]     rq_tag,
    output wire [7:0]         rq_src,
    output wire [8*16-1:0]    rq_rg,
    input  wire [64*34-1:0]   rd_w,
    input  wire [64*34-1:0]   rd_k,
    input  wire [64*16-1:0]   rd_x,
    input  wire               o_cr,
    output wire               o_v,
    output wire [15:0]        o_rg,
    output wire [3:0]         o_tag,
    output wire [3:0]         o_mask,
    output wire [4*32-1:0]    o_y,
    output wire [4*16-1:0]    o_bf,
    output wire [3:0]         o_f,
    output wire [31:0]        o_cnt_rom,
    output wire [31:0]        o_cnt_stream,
    output wire               idle
);
    ot_hdc_v41x_wgt_mtop #(.POOL(1)) u (
        .clk(clk), .rst_n(rst_n), .d_v(d_v), .d_rdy(d_rdy), .d_plg(d_plg), .d_nb(d_nb), .d_nrows(d_nrows),
        .d_wbase(d_wbase), .d_ind(d_ind), .d_eid(d_eid), .d_estride(d_estride), .d_tag(d_tag), .d_src(d_src),
        .rq_v(rq_v), .rq_a(rq_a), .rq_q(rq_q), .rq_plg(rq_plg), .rq_tag(rq_tag), .rq_src(rq_src), .rq_rg(rq_rg),
        .rd_w(rd_w), .rd_k(rd_k), .rd_x(rd_x),
        .o_cr(o_cr), .o_v(o_v), .o_rg(o_rg), .o_tag(o_tag), .o_mask(o_mask), .o_y(o_y), .o_bf(o_bf), .o_f(o_f),
        .o_cnt_rom(o_cnt_rom), .o_cnt_stream(o_cnt_stream), .idle(idle));
endmodule
