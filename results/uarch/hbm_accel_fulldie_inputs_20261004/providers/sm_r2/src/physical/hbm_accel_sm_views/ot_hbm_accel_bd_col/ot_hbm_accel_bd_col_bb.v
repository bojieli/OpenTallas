`timescale 1ns/1ps
// Blackbox view of the hardened block-dot column macro ot_hbm_accel_bd_col (rtl/hbm_accel/sm/ot_hbm_accel_bd_col.sv, LB 2, IL 8, TAGW 16)
// for the hierarchical route of the SM element; LEF / SS / FF / TT timing models beside this file (abstract.sh).
(* blackbox *)
module ot_hbm_accel_bd_col (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              v,
    input  wire              first,
    input  wire              last,
    input  wire              fp4,
    input  wire [15:0]       tag,
    input  wire [511:0]      wq,
    input  wire [19:0]       we,
    input  wire [511:0]      xq,
    input  wire [19:0]       xe,
    output wire              ov,
    output wire [31:0]       y,
    output wire [15:0]       otag,
    output wire              fault
);
endmodule
