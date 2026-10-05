`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// W11 serial-domain wrappers over the fast binary32 units (rtl/hdc/ot_hdc_fastfp.sv), kept out of that file so
// the records that pin it stay current.  Needs rtl/hdc/ot_hdc_fastfp.sv (or its DPI stand-ins); the non-default
// branches also need rtl/hdc/ot_hdc_fp32_mul_lat.sv, rtl/hdc/ot_hdc_fp32_add_lat.sv and rtl/hdc/ot_hdc_prefix.sv.
//   ot_hdc_qmul_lat #(LAT)       ot_hdc_qmul at LAT 3 (default), ot_hdc_fp32_mul_lat4 / _lat5i / _lat #(LAT)
//   ot_hdc_qadd_lat #(KEEP, LAT) ot_hdc_qadd (default), ot_hdc_fp32_add_lat3 / _lat4i (keep-prefix adders)
//   ot_hdc_kadd / _kge / _kinc   integer add / compare / increment: behavioural (K = 0) or keep-prefix (K = 1)
// ---------------------------------------------------------------------------
// ot_hdc_qmul_lat #(LAT): ot_hdc_qmul with the multiplier's latency as a parameter.  LAT = 3 is ot_hdc_qmul
// itself (ot_hdc_fp32_mul_fast); LAT = 4..7 is ot_hdc_fp32_mul_lat #(LAT) (rtl/hdc/ot_hdc_fp32_mul_lat.sv, which
// needs rtl/hdc/ot_hdc_fp32_add_lat.sv), bit-identical to it (21d9aab2: 5,000,000 biased pairs).  W11 serial
// domain: the 3-stage multiply misses 1.111 ns at SS; LAT 4 reaches 987 MHz.
module ot_hdc_qmul_lat #(
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (LAT == 3) begin : g_l3
        ot_hdc_fp32_mul_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_l4
        // the fixed LAT-4 top: a plain module name, so synthesis can keep it as its own hierarchy
        // (ORFS SYNTH_KEEP_MODULES) and ABC maps it as the standalone unit
        ot_hdc_fp32_mul_lat4 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 5) begin : g_l5
        // LAT 5 is the input-cut variant (C1 + C3; rtl/hdc/ot_hdc_fp32_mul_lat.sv): the operand multiplexer ahead of
        // the unit shares a stage with the decode / normalise, not with the partial products (W11 serial domain)
        ot_hdc_fp32_mul_lat5i u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_ln
        ot_hdc_fp32_mul_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// ot_hdc_qadd_lat #(KEEP, LAT): ot_hdc_qadd, or (KEEP = 1) the plain ot_hdc_fp32_add_lat3 top of
// rtl/hdc/ot_hdc_fp32_add_lat.sv (needs rtl/hdc/ot_hdc_prefix.sv): the same binary32 add, bit for bit, with
// (* keep *) Kogge-Stone prefix adders that ABC cannot re-ripple inside a parent block; LAT = 4 (KEEP = 1) is
// the input-cut ot_hdc_fp32_add_lat4i (W11 serial domain, 0.9 GHz at SS).
module ot_hdc_qadd_lat #(
    parameter integer KEEP = 0,
    parameter integer LAT = 3
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        v,
    input  wire [31:0] a,
    input  wire [31:0] b,
    output wire [31:0] y,
    output wire        fault
);
    wire [1:0] err;
    wire vo;
    generate if (KEEP == 0) begin : g_fast
        ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_keep4
        ot_hdc_fp32_add_lat4i u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_keep
        ot_hdc_fp32_add_lat3 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Keep-prefix integer arithmetic for the W11 serial-domain build (K = 1: rtl/hdc/ot_hdc_prefix.sv, whose
// (* keep *) Kogge-Stone levels ABC cannot re-ripple; K = 0: the behavioural operator, the unit as it was).
module ot_hdc_kadd #(parameter integer W = 24, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire cin, output wire [W-1:0] s, output wire cout
);
    generate if (K == 0) begin : g_b
        assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
    end else begin : g_k
        ot_hdc_ksadd_k #(.W(W)) u (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
    end endgenerate
endmodule

// ge = (a >= b), unsigned
module ot_hdc_kge #(parameter integer W = 32, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, output wire ge
);
    generate if (K == 0) begin : g_b
        assign ge = (a >= b);
    end else begin : g_k
        wire [W-1:0] unused_s;
        ot_hdc_ksadd_k #(.W(W)) u (.a(a), .b(~b), .cin(1'b1), .s(unused_s), .cout(ge));
    end endgenerate
endmodule

// y = a + inc (mod 2^W)
module ot_hdc_kinc #(parameter integer W = 16, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire inc, output wire [W-1:0] y
);
    generate if (K == 0) begin : g_b
        assign y = a + {{(W-1){1'b0}}, inc};
    end else begin : g_k
        wire unused_co;
        ot_hdc_inc_k #(.W(W)) u (.a(a), .inc(inc), .y(y), .co(unused_co));
    end endgenerate
endmodule
