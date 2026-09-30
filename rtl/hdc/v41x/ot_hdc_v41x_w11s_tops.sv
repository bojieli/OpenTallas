`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 streaming-domain (1.2 GHz at SS) hardening tops for the latency-cut
// arithmetic units of the V4.1 indexer and attention tile: each wraps one unit
// with a clock/reset port pair (the physical runner false-paths rst_n) and
// registered-output semantics identical to the unit's own.  Hardening vehicles
// only; the units themselves are instantiated directly by the datapath.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_w11s_q4dot #(parameter integer QL = 3) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire [127:0] a,
    input  wire [127:0] b,
    input  wire [7:0]   ua,
    input  wire [7:0]   ub,
    output wire [31:0]  y,
    output wire         ovf
);
    ot_hdc_v41x_q4dot #(.QL(QL)) u (.clk(clk), .a(a), .b(b), .ua(ua), .ub(ub), .y(y), .ovf(ovf));
endmodule

module ot_hdc_v41x_w11s_bmul #(parameter integer ML = 3) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] a,
    input  wire [15:0] w,
    output wire [15:0] y,
    output wire        ovf
);
    ot_hdc_v41x_bmul #(.ML(ML)) u (.clk(clk), .a(a), .w(w), .y(y), .ovf(ovf));
endmodule

module ot_hdc_v41x_w11s_attn_bmul #(parameter integer ML = 3) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] a,
    input  wire [15:0] b,
    input  wire        pad,
    output wire [31:0] y,
    output wire        flt
);
    ot_hdc_v41x_attn_bmul #(.ML(ML)) u (.clk(clk), .a(a), .b(b), .pad(pad), .y(y), .flt(flt));
endmodule
