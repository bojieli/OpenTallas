`timescale 1ns/1ps
// Blackbox view of the hardened BF16 column macro ot_hbm_accel_tc16 (rtl/hbm_accel/sm/ot_hbm_accel_tc16.sv) for the
// hierarchical route of the SM element; LEF / SS / FF / TT timing models beside this file (routed leaf, abstract.sh).
(* blackbox *)
module ot_hbm_accel_tc16 (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          v,
    input  wire          first,
    input  wire          last,
    input  wire [15:0]   tag,
    input  wire [255:0]  w,
    input  wire [255:0]  x,
    output wire          ov,
    output wire [31:0]   y,
    output wire [15:0]   otag,
    output wire          fault
);
endmodule
