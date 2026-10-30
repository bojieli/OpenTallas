module ot_hdc_fp32_add_lat3 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                             output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_add_lat #(.LAT(3)) u (.*);
endmodule
