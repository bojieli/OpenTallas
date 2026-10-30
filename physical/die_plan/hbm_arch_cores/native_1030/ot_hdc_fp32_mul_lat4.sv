
module ot_hdc_fp32_mul_lat4 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(4)) u (.*);
endmodule
