`timescale 1ns/1ps
// Distinct current-source gate-only native leaf. Historical943 view is preserved.
module qfd_su_sfu_rsq_native45 #(
    parameter integer LA = 4,
    parameter integer LM = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] x,
    output reg  [31:0] y,
    output reg         vo,
    output reg         fault
);
 ot_hdc_sfu_rsq_t #(.LA(LA),.LM(LM))u_body(
 .clk(clk),
 .rst_n(rst_n),
 .v(v),
 .x(x),
 .y(y),
 .vo(vo),
 .fault(fault)
 );
endmodule
