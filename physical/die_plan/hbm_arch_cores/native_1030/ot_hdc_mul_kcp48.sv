
// KCP copy of the C1 operand register: kept (SYNTH_KEEP_MODULES) so equal-D copies are never merged into one driver
module ot_hdc_mul_kcp48 (input wire clk, input wire rst_n, input wire [47:0] d, output reg [47:0] q);
    always @(posedge clk or negedge rst_n) if (!rst_n) q <= 48'd0; else q <= d;
endmodule
