
// the W11 serial-domain LAT-5 multiplier: the LAT-4 cuts plus C1 (after the decode / normalise), bit-identical
module ot_hdc_fp32_mul_lat5i (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                              output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_lat #(.LAT(5), .CUTS(5)) u (.*);
endmodule
