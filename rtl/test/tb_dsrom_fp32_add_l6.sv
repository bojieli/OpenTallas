`timescale 1ns/1ps
// ot_dsrom_fp32_add_f12_l6 (CUTS 7'b1101011) against ot_hdc_fp32_add_fast delayed to LAT 6, every output bit
// ({valid_out, err, y}); stimulus rtl/test/tb_dsrom_fp32_add_l6.cpp (the biased pairs of tb_su_fp32_f12.cpp).
module tb_dsrom_fp32_add_l6 (input wire clk, input wire rst_n, input wire v, input wire [31:0] a, input wire [31:0] b,
                             output wire mism);
    wire [31:0] ya, y6; wire [1:0] ea, e6; wire va, v6;
    ot_hdc_fp32_add_fast u_ra (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(ya), .err(ea), .valid_out(va));
    ot_dsrom_fp32_add_f12_l6 u6 (.clk(clk), .rst_n(rst_n), .valid_in(v), .a(a), .b(b), .y(y6), .err(e6), .valid_out(v6));
    reg [34:0] da [1:3];
    integer i;
    always @(posedge clk) begin
        da[1] <= {va, ea, ya};
        for (i = 2; i <= 3; i = i + 1) da[i] <= da[i-1];
    end
    assign mism = rst_n && ({v6, e6, y6} != da[3]);
endmodule
