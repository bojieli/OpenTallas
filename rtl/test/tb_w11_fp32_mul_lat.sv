`timescale 1ns/1ps
// W11: ot_hdc_fp32_mul_lat #(LAT = 3..7) against ot_hdc_fp32_mul_fast, cycle-aligned, every output bit.
// Stimulus from the C++ driver (random encodings biased to specials, subnormals, near-cancellation, ties).
module tb_w11_fp32_mul_lat (input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
                            output wire [4:0] mism, output wire ref_v);
    wire [31:0] yr; wire [1:0] er;
    ot_hdc_fp32_mul_fast u_ref (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(yr), .err(er), .valid_out(ref_v));
    // the reference delayed to each LAT
    reg [34:0] d1, d2, d3, d4;
    always @(posedge clk) begin d1 <= {ref_v, er, yr}; d2 <= d1; d3 <= d2; d4 <= d3; end
    genvar L;
    generate for (L = 3; L <= 7; L = L + 1) begin : g
        wire [31:0] y; wire [1:0] e; wire vo;
        ot_hdc_fp32_mul_lat #(.LAT(L)) u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(e), .valid_out(vo));
        wire [34:0] want = (L == 3) ? {ref_v, er, yr} : (L == 4) ? d1 : (L == 5) ? d2 : (L == 6) ? d3 : d4;
        assign mism[L-3] = rst_n && ({vo, e, y} != want);
    end endgenerate
endmodule
