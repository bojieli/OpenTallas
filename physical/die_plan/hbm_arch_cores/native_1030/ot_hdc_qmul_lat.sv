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
