// CLAUDE HBM-ABSTRACTS hub margin (2026-10-06): + the rounding-increment cut (bit 7): the round / encode stage behind
// u_k6 was the routed HC lane's critical path at ML 6 (m8hc SS@833 +3.8 ps)
module ot_hdc_fp32_mul_f12_l7 (input wire clk, rst_n, valid_in, input wire [31:0] a, b, output wire [31:0] y,
                               output wire [1:0] err, output wire valid_out);
    ot_hdc_fp32_mul_f12 #(.CUTS(8'b11101011)) u (.*);
endmodule
