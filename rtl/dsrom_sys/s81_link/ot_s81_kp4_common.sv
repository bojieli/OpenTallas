`timescale 1ns/1ps
// ---------------------------------------------------------------------------------------------------------------
// ot_s81_kp4_common (S81-KP4 2026-10-17): shared cells of the S81 die-link KP4 FEC tiles ot_s81_kp4_enc / ot_s81_kp4_dec.
//   ot_s81_kp4_rst   regional SYNCHRONOUS reset tree (owner die standard 10-16, item 2): the reset port is sampled by two
//                    flops, then fans out through NL kept leaf flops of EQUAL depth; each leaf resets one region's
//                    control registers synchronously.  No asynchronous reset fanout; datapath registers carry no reset.
//   ot_s81_kp4_cmul  a * alpha^E (constant GF(2^10) multiplier, p = x^10 + x^3 + 1)
//   ot_s81_kp4_vmul  a * b
//   ot_s81_kp4_inv   a^-1 (0 -> 0); kept hierarchy: yosys must not merge the driving register into an inferred ROM
// ---------------------------------------------------------------------------------------------------------------
module ot_s81_kp4_rst #(parameter integer NL = 4) (
    input  wire          clk,
    input  wire          rst_n,     // die reset copy (synchronous to clk)
    output wire [NL-1:0] rs_n       // leaf copies, 3 flops after the port
);
    reg r1, r2;
    (* keep *) reg [NL-1:0] lf;
    always @(posedge clk) begin r1 <= rst_n; r2 <= r1; lf <= {NL{r2}}; end
    assign rs_n = lf;
endmodule
module ot_s81_kp4_cmul #(parameter integer E = 0) (input wire [9:0] a, output wire [9:0] y);
`include "ot_s81_gf1024.svh"
    localparam [9:0] C = gf_alpha(((E % 1023) + 1023) % 1023);
    assign y = gf_mul(a, C);
endmodule
module ot_s81_kp4_vmul (input wire [9:0] a, input wire [9:0] b, output wire [9:0] y);
`include "ot_s81_gf1024.svh"
    assign y = gf_mul(a, b);
endmodule
(* keep_hierarchy *)
module ot_s81_kp4_inv (input wire [9:0] a, output reg [9:0] y);
`include "ot_s81_gf1024.svh"
    always @* y = gf_inv(a);
endmodule
