`timescale 1ns/1ps
// qwen-coll-io r3 2026-10-14: qfd_io_collective -- the Qwen TP8 compute-die collective master under its DIE NAME (owner
// 10-14 no-stub rule: every die instance binds to real RTL of its name, every die net lands on a real port).
// = ot_coll_tp8_die in the production shape, no parameters (one hardened cluster for all 8 compute dies):
//   WT 3      pin-registered data leaves ot_coll_tp8_col_tile_r3 x4 + flat metadata column beside the controller
//   DEPTH 64  engine column leaves ot_coll_col_tile_d64 x5 (one board crossing per 64-word owner half, LAT 339)
//   LQD/TQD 128 result reservations
//   STRAP 1   the package rank / die-in-package come from the static straps pkg_s / die_ps (die bumps), not parameters
// Measured (tools/qwen_coll_tp8_bench.py --wrapper-columns 3 --strap [--qfd]): 8-rank exact golden; Qwen AR256 /
// 2 x AR256 / argmax at board LAT 339 with link-level credits; see results/rtl/qwen_coll_io_1014/.
// Link credit domains (io_xfifo design input): the SerDes / UCIe ports assume end-to-end credits sized by the far
// queue (P 64, R 32, SerDes = engine DEPTH 64); io_xfifo channels are hop-by-hop converters (IBUF = sender credits,
// OCRED = receiver queue; the board BDP buffer stays in the link adapter).
module qfd_io_collective (
    input  wire              clk, // parent controller root
    input wire clk_colr0, clk_colr1, clk_colr2, clk_colr3, clk_ecol0, clk_ecol1, clk_ecol2, clk_ecol3, clk_ecol4, clk_pfold0, clk_pfold1, clk_pfold2, clk_pfold3, clk_efold0, clk_efold1, clk_efold2, clk_efold3,
    input  wire              rst_n,
    input  wire [1:0]        pkg_s,
    input  wire              die_ps,
    input  wire              in_valid,
    output wire              in_cr,
    input  wire [511:0]      in_data,
    input  wire              in_last,
    input  wire              in_mode,
    input  wire [31:0]       in_tag,
    output wire              up_valid,
    output wire [545:0]      up_rec,
    input  wire              up_ready,
    input  wire              up_cr_in,
    input  wire              dp_valid,
    input  wire [545:0]      dp_rec,
    output wire              dp_cr_out,
    output wire              ur_valid,
    output wire [513:0]      ur_rec,
    input  wire              ur_ready,
    input  wire              ur_cr_in,
    input  wire              dr_valid,
    input  wire [513:0]      dr_rec,
    output wire              dr_cr_out,
    output wire [2:0]        sx_valid,
    output wire [1637:0]     sx_rec,
    input  wire [2:0]        sx_ready,
    input  wire [2:0]        sx_cr_in,
    input  wire [2:0]        sr_valid,
    input  wire [1637:0]     sr_rec,
    output wire [2:0]        sr_cr_out,
    output wire              out_valid,
    output wire [511:0]      out_data,
    output wire              out_last,
    output wire [2:0]        out_rank,
    output wire              out_err,
    output wire              fault,
    output wire [4:0]        fault_code
);
    ot_coll_tp8_die #(.PKG(0), .DIE(0), .LANES(16), .TAGW(32), .WT(3), .CT(1), .DEPTH(64), .LQD(128), .TQD(128),
        .STRAP(1), .CCLK(1)) u_coll (
        .clk(clk),
        .clk_colr({clk_colr3,clk_colr2,clk_colr1,clk_colr0}),
        .clk_ecol({clk_ecol4,clk_ecol3,clk_ecol2,clk_ecol1,clk_ecol0}),
        .clk_pfold({clk_pfold3,clk_pfold2,clk_pfold1,clk_pfold0}),
        .clk_efold({clk_efold3,clk_efold2,clk_efold1,clk_efold0}),
        .rst_n(rst_n), .pkg_s(pkg_s), .die_ps(die_ps),
        .in_valid(in_valid), .in_cr(in_cr), .in_data(in_data), .in_last(in_last), .in_mode(in_mode), .in_tag(in_tag),
        .up_valid(up_valid), .up_rec(up_rec), .up_ready(up_ready), .up_cr_in(up_cr_in),
        .dp_valid(dp_valid), .dp_rec(dp_rec), .dp_cr_out(dp_cr_out),
        .ur_valid(ur_valid), .ur_rec(ur_rec), .ur_ready(ur_ready), .ur_cr_in(ur_cr_in),
        .dr_valid(dr_valid), .dr_rec(dr_rec), .dr_cr_out(dr_cr_out),
        .sx_valid(sx_valid), .sx_rec(sx_rec), .sx_ready(sx_ready), .sx_cr_in(sx_cr_in),
        .sr_valid(sr_valid), .sr_rec(sr_rec), .sr_cr_out(sr_cr_out),
        .out_valid(out_valid), .out_data(out_data), .out_last(out_last), .out_rank(out_rank), .out_err(out_err),
        .fault(fault), .fault_code(fault_code));
endmodule
