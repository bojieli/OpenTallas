// Integration-only c12 namespace export. Canonical source: rtl/hdc/ot_hdc_fastfp_lat_c12.sv
`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// HBM SU 1.2 GHz closure (claude hbm-su-attn, 2026-10-05): FILE SWAP of rtl/hdc/ot_hdc_fastfp_lat.sv for the
// c12 build -- rtl/hdc/ot_hdc_fastfp_lat_f12.sv (unchanged, pinned by the DS ROM records) plus one mapping: the
// keep-prefix adder at LAT 6 is ot_hbm_selected_c12__ot_hdc_fp32_add_f12_l6x (rtl/hdc/v41x/ot_dsrom_su_add6.sv: the _l5x cut set plus a
// cut between the magnitude compare and the alignment, the DS ROM closure kit's six-stage adder).  In the routed
// SU blocks at ALAT 5 the _l5x adder's compare / alignment / swap stage missed 0.833 ns by 3-43 ps in context.
// Same function, same latency per LAT, so a unit built from this file is bit-identical to one built from the
// original (rtl/test/tb_su_fp32_f12.sv / the SU campaigns).  A source list names this file OR an original, never
// both.  Needs rtl/hdc/ot_hdc_fp32_f12.sv and rtl/hdc/v41x/ot_dsrom_su_add6.sv.
// ---------------------------------------------------------------------------
// ot_hbm_selected_c12__ot_hdc_qmul_lat #(LAT): ot_hbm_selected_c12__ot_hdc_qmul with the multiplier's latency as a parameter.  LAT = 3 is ot_hbm_selected_c12__ot_hdc_qmul
// itself (ot_hbm_selected_c12__ot_hdc_fp32_mul_fast); LAT = 4..7 is ot_hdc_fp32_mul_lat #(LAT) (rtl/hdc/ot_hdc_fp32_mul_lat.sv, which
// needs rtl/hdc/ot_hdc_fp32_add_lat.sv), bit-identical to it (21d9aab2: 5,000,000 biased pairs).  W11 serial
// domain: the 3-stage multiply misses 1.111 ns at SS; LAT 4 reaches 987 MHz.
module ot_hbm_selected_c12__ot_hdc_qmul_lat #(
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
        ot_hbm_selected_c12__ot_hdc_fp32_mul_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_l4
        // the fixed LAT-4 top: a plain module name, so synthesis can keep it as its own hierarchy
        // (ORFS SYNTH_KEEP_MODULES) and ABC maps it as the standalone unit
        ot_hdc_fp32_mul_lat4 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 5) begin : g_l5
        // 1.2 GHz: decode..normalise | rows + 5 CSA | 2 CSA + 48-bit add | select / subnormal | round + encode
        ot_hbm_selected_c12__ot_hdc_fp32_mul_f12_l5 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 6) begin : g_l6
        // 1.2 GHz lane build: the lane's operand multiplexer + decode + fraction LZC | normalise, powers | rows + 5 CSA |
        // 2 CSA + 48-bit add | select / subnormal | round + encode (an input register in front of the LAT-5 unit
        // missed by 12 ps: its decode / LZC / normalise stage is the longest)
        ot_hbm_selected_c12__ot_hdc_fp32_mul_f12_l6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_ln
        ot_hdc_fp32_mul_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// ot_hbm_selected_c12__ot_hdc_qadd_lat #(KEEP, LAT): ot_hbm_selected_c12__ot_hdc_qadd, or (KEEP = 1) the plain ot_hdc_fp32_add_lat3 top of
// rtl/hdc/ot_hdc_fp32_add_lat.sv (needs rtl/hdc/ot_hdc_prefix.sv): the same binary32 add, bit for bit, with
// (* keep *) Kogge-Stone prefix adders that ABC cannot re-ripple inside a parent block; LAT = 4 (KEEP = 1) is
// the input-cut ot_hdc_fp32_add_lat4i (W11 serial domain, 0.9 GHz at SS).
module ot_hbm_selected_c12__ot_hdc_qadd_lat #(
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
        ot_hbm_selected_c12__ot_hdc_fp32_add_fast u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 4) begin : g_keep4
        // 1.2 GHz: decode..swap | add + LZC | shift + round | encode
        ot_hbm_selected_c12__ot_hdc_fp32_add_f12_l4 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 5) begin : g_keep5
        // 1.2 GHz lane build: the lane's operand multiplexer + decode + exponent differences | compare, alignments,
        // swap | add, LZC | shift, round | encode (an input register in front of the LAT-4 unit missed by 21-50 ps)
        ot_hbm_selected_c12__ot_hdc_fp32_add_f12_l5x u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 6) begin : g_keep6
        // 1.2 GHz c12 build: decode, exponent differences | compare | alignments, swap | add, LZC | shift, round |
        // encode
        ot_hbm_selected_c12__ot_hdc_fp32_add_f12_l6x u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else if (LAT == 3) begin : g_keep
        ot_hdc_fp32_add_lat3 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_keepn
        ot_hdc_fp32_add_lat #(.LAT(LAT)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err),
                                            .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule

// Keep-prefix integer arithmetic for the W11 serial-domain build (K = 1: rtl/hdc/ot_hdc_prefix.sv, whose
// (* keep *) Kogge-Stone levels ABC cannot re-ripple; K = 0: the behavioural operator, the unit as it was).
module ot_hbm_selected_c12__ot_hdc_kadd #(parameter integer W = 24, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, input wire cin, output wire [W-1:0] s, output wire cout
);
    generate if (K == 0) begin : g_b
        assign {cout, s} = {1'b0, a} + {1'b0, b} + {{W{1'b0}}, cin};
    end else begin : g_k
        ot_hbm_selected_c12__ot_hdc_ksadd_k #(.W(W)) u (.a(a), .b(b), .cin(cin), .s(s), .cout(cout));
    end endgenerate
endmodule

// ge = (a >= b), unsigned
module ot_hbm_selected_c12__ot_hdc_kge #(parameter integer W = 32, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire [W-1:0] b, output wire ge
);
    generate if (K == 0) begin : g_b
        assign ge = (a >= b);
    end else begin : g_k
        wire [W-1:0] unused_s;
        ot_hbm_selected_c12__ot_hdc_ksadd_k #(.W(W)) u (.a(a), .b(~b), .cin(1'b1), .s(unused_s), .cout(ge));
    end endgenerate
endmodule

// y = a + inc (mod 2^W)
module ot_hbm_selected_c12__ot_hdc_kinc #(parameter integer W = 16, parameter integer K = 0) (
    input  wire [W-1:0] a, input wire inc, output wire [W-1:0] y
);
    generate if (K == 0) begin : g_b
        assign y = a + {{(W-1){1'b0}}, inc};
    end else begin : g_k
        wire unused_co;
        ot_hbm_selected_c12__ot_hdc_inc_k #(.W(W)) u (.a(a), .inc(inc), .y(y), .co(unused_co));
    end endgenerate
endmodule
