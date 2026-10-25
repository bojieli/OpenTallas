// HBM-W128 2026-10-25: valid-masked equivalence of ot_hdc_fp32_mul_lat LAT 8, DRST 1 (gold, data reset) vs DRST 0
// (gate, valid-only reset).  ok: valid_out equal every cycle, y/err equal whenever valid_out.
module mul_miter (input wire clk, input wire rst_n, input wire valid_in, input wire [31:0] a, input wire [31:0] b,
                  output wire ok);
    wire [31:0] yg, yt; wire [1:0] eg, et; wire vg, vt;
    ot_hdc_fp32_mul_lat #(.LAT(8), .DRST(1)) u_g (.clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b),
        .y(yg), .err(eg), .valid_out(vg));
`ifdef MUT_VALID
    ot_hdc_fp32_mul_lat_mv #(.LAT(8), .DRST(0)) u_t (
`elsif MUT_DATA
    ot_hdc_fp32_mul_lat_md #(.LAT(8), .DRST(0)) u_t (
`else
    ot_hdc_fp32_mul_lat #(.LAT(8), .DRST(0)) u_t (
`endif
        .clk(clk), .rst_n(rst_n), .valid_in(valid_in), .a(a), .b(b), .y(yt), .err(et), .valid_out(vt));
    assign ok = (vg == vt) && (!vg || ((yg == yt) && (eg == et)));
endmodule
