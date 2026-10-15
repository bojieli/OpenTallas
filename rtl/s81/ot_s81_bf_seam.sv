`timescale 1ns/1ps
// Fixed BF front-to-column egress. Replicate once on each physical face.
module ot_s81_bf_seam #(parameter integer W=776, PIPE=0) (
    input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    if (PIPE != 0) begin : g_pin
        (* keep = 1, dont_touch = 1 *) reg [W-1:0] r;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) r <= '0;
`ifdef BF_SEAM_MUTANT_DATA
            else r <= d ^ ({{(W-1){1'b0}},1'b1} << (W/2));
`elsif BF_SEAM_MUTANT_SLOT
            else r <= d ^ ({{(W-1){1'b0}},1'b1} << (W-1));
`else
            else r <= d;
`endif
        assign q = r;
    end else begin : g_direct
        assign q = d;
    end
endmodule
