`timescale 1ns/1ps
module ot_fp32_signed_add_differential_top (
    input  wire [31:0] left_code,
    input  wire [31:0] right_code,
    output wire [33:0] result
);
    import ot_fp32_rne_pkg::*;

    assign result = fp32_add_rne(left_code, right_code);
endmodule
