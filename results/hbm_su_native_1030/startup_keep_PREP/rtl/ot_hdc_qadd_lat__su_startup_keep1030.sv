
// ot_hdc_qadd_lat #(KEEP, LAT): ot_hdc_qadd, or (KEEP = 1) the plain ot_hdc_fp32_add_lat3 top of
// rtl/hdc/ot_hdc_fp32_add_lat.sv (needs rtl/hdc/ot_hdc_prefix.sv): the same binary32 add, bit for bit, with
// (* keep *) Kogge-Stone prefix adders that ABC cannot re-ripple inside a parent block; LAT = 4 (KEEP = 1) is
// the input-cut ot_hdc_fp32_add_lat4i (W11 serial domain, 0.9 GHz at SS).
module ot_hdc_qadd_lat__su_startup_keep1030 #(
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
        ot_hdc_fp32_add_lat4i__su_startup_keep1030 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end else begin : g_keep
        ot_hdc_fp32_add_lat3 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
    end endgenerate
    assign fault = vo && (err != 2'd0);
endmodule
