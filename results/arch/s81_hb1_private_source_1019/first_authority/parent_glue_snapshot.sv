`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------------
// PL-SLICE (PARENTS-LANDED sub-lane, 10-18): the slice glue flops of ot_s81sl_slice moved into three tiny children so the
// flat parent ot_s81sl_slice_c{1,3}x is wires-only for tools/landed_parent/lp.py.  Same logic, same edges:
//   ot_s81sl_ckf   forwarded clock branches (the original assign ck_* = {N{clk}}): one clock output per lane
//   ot_s81sl_mk    x-chain epoch marker (the original mkq: a registered relay of the released reset)
//   ot_s81sl_sflt  slice fault = registered OR of the sub-leaf sticky faults (the original flt)
// ---------------------------------------------------------------------------------------------------------------------
module ot_s81sl_ckf (
    input  wire        clk,
    output wire [15:0] ck_line,
    output wire [1:0]  ck_v,
    output wire [15:0] ck_xc,
    output wire [7:0]  ck_rt
);
    assign ck_line = {16{clk}}; assign ck_v = {2{clk}}; assign ck_xc = {16{clk}}; assign ck_rt = {8{clk}};
endmodule

module ot_s81sl_mk (
    input  wire       clk,
    input  wire       rst_n,
    output reg  [1:0] mk
);
    always @(posedge clk or negedge rst_n) if (!rst_n) mk <= 2'b00; else mk <= {mk[0], 1'b1};
endmodule

module ot_s81sl_sflt #(parameter integer N = 10) (
    input  wire         clk,
    input  wire [N-1:0] f,
    output wire         q
);
    reg r;
    always @(posedge clk) r <= |f;
    assign q = r;
endmodule
