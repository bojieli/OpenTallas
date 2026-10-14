`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_dsrom_su_softmax_add6: the six-cut f12 binary32 adder (the _l5x cut set of rtl/hdc/ot_hdc_fp32_f12.sv plus a
// cut between the magnitude compare and the alignment, CUTS bit 0), as a fixed top for the softmax unit
// (ot_dsrom_su_softmax ADD6 = 1).  LAT 6, same function as every other cut set of the same module (bit for bit).
// Used for the adds whose operands come out of another unit (the per-lane max hold, the row-sum tree, the
// denominator, the RoPE tail), where the routed context adds a register-to-register path the LAT-4/LAT-5 cuts do
// not close: the coordinator's rule after su_norm.
// ---------------------------------------------------------------------------
module ot_dsrom_su_softmax_add6 (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        valid_in,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire [1:0]  err,
    output wire        valid_out
);
    ot_hdc_fp32_add_f12 #(.CUTS(7'b1101011)) u (.*);
endmodule
