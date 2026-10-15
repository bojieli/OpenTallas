`timescale 1ns/1ps
// qwen-coll-io r4 2026-10-14 (OWNER 0ah static cycle schedule): qfd_io_collective_static -- the Qwen TP8 compute-die
// collective master under its die name, = ot_coll_tp8_static in the production shape, no parameters: one master for
// all 8 compute dies (rank from the pkg_s / die_ps straps), each of the 8 hardened ot_coll_fold_slice children on its
// own clock entry.  NO credit / ready ports: a compiler command per message (cmd_*), producer words at their compiled
// slots, links as valid + record at fixed latencies.  LU / LS are the die's priced link latencies (compute-die lead):
// LU = UCIe up-register -> peer dp pin incl. both static CDC channels, LS = SerDes sx-register -> peer sr pin.
// Successor of qfd_io_collective (credit design, historical/diagnostic under 0ah).
module qfd_io_collective_static (
    input  wire          clk,                   // parent root
    input  wire          clk_pfold0, clk_pfold1, clk_pfold2, clk_pfold3,
    input  wire          clk_xfold0, clk_xfold1, clk_xfold2, clk_xfold3,
    input  wire          rst_n,
    input  wire [1:0]    pkg_s,
    input  wire          die_ps,
    input  wire          cmd_v,
    input  wire          cmd_mode,
    input  wire [15:0]   cmd_words,
    input  wire [31:0]   cmd_tag,
    input  wire          in_valid,
    input  wire [511:0]  in_data,
    input  wire          in_last,
    input  wire          in_mode,
    input  wire [31:0]   in_tag,
    output wire          up_valid,
    output wire [545:0]  up_rec,
    input  wire          dp_valid,
    input  wire [545:0]  dp_rec,
    output wire          ur_valid,
    output wire [513:0]  ur_rec,
    input  wire          dr_valid,
    input  wire [513:0]  dr_rec,
    output wire [2:0]    sx_valid,
    output wire [1637:0] sx_rec,
    input  wire [2:0]    sr_valid,
    input  wire [1637:0] sr_rec,
    output wire          out_valid,
    output wire [511:0]  out_data,
    output wire          out_last,
    output wire [2:0]    out_rank,
    output wire          out_err,
    output wire          fault,
    output wire [4:0]    fault_code
);
`ifndef OT_QFDS_LU
`define OT_QFDS_LU 28
`endif
`ifndef OT_QFDS_LS
`define OT_QFDS_LS 352
`endif
    ot_coll_tp8_static #(.LANES(16), .TAGW(32), .ADD_LAT(7), .LU(`OT_QFDS_LU), .LS(`OT_QFDS_LS), .GC(8), .CCLK(1)) u_coll (
        .clk(clk), .clk_pfold({clk_pfold3, clk_pfold2, clk_pfold1, clk_pfold0}),
        .clk_xfold({clk_xfold3, clk_xfold2, clk_xfold1, clk_xfold0}),
        .rst_n(rst_n), .pkg_s(pkg_s), .die_ps(die_ps),
        .cmd_v(cmd_v), .cmd_mode(cmd_mode), .cmd_words(cmd_words), .cmd_tag(cmd_tag),
        .in_valid(in_valid), .in_data(in_data), .in_last(in_last), .in_mode(in_mode), .in_tag(in_tag),
        .up_valid(up_valid), .up_rec(up_rec), .dp_valid(dp_valid), .dp_rec(dp_rec),
        .ur_valid(ur_valid), .ur_rec(ur_rec), .dr_valid(dr_valid), .dr_rec(dr_rec),
        .sx_valid(sx_valid), .sx_rec(sx_rec), .sr_valid(sr_valid), .sr_rec(sr_rec),
        .out_valid(out_valid), .out_data(out_data), .out_last(out_last), .out_rank(out_rank), .out_err(out_err),
        .fault(fault), .fault_code(fault_code));
endmodule
