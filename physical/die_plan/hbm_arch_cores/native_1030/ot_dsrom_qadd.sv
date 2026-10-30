
// ot_dsrom_qadd #(LAT): the binary32 add of the fused pipelines.  LAT 6: ot_dsrom_fp32_add_f12_l6; otherwise the
// keep-prefix ot_hdc_qadd_lat (LAT 4: f12_l4, LAT 5: f12_l5x through rtl/hdc/ot_hdc_fastfp_lat_f12.sv).
module ot_dsrom_qadd #(parameter integer LAT = 4) (
    input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b, output wire [31:0] y,
    output wire fault
);
    generate if (LAT == 6) begin : g6
        wire [1:0] err;
        wire vo;
        ot_dsrom_fp32_add_f12_l6 u (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y), .err(err), .valid_out(vo));
        assign fault = vo && (err != 2'd0);
    end else begin : gq
        ot_hdc_qadd_lat #(.KEEP(1), .LAT(LAT)) u (clk, rst_n, v, a, b, y, fault);
    end endgenerate
endmodule
