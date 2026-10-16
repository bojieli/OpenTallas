`timescale 1ns/1ps
// Fixed BF front-to-column egress. Replicate once on each physical face.
module ot_s81_bf_seam #(parameter integer W=776, PIPE=0) (
    input wire clk, rst_n, input wire [W-1:0] d, output wire [W-1:0] q
);
    if (PIPE != 0) begin : g_pin
        // Reset relays per face: one relay flop per RG-bit group (gate ec84ce526: a single relay drove 775 loads > 256),
        // all released on the same edge, so every bit clears and releases exactly as with one relay (0 cycles).
        localparam integer RG = 160, NRL = (W + RG - 1) / RG;
        (* keep = 1, dont_touch = 1 *) reg [NRL-1:0] rst_local;
        always @(posedge clk or negedge rst_n)
            if (!rst_n) rst_local <= '0; else rst_local <= '1;
        (* keep = 1, dont_touch = 1 *) reg [W-1:0] r;
        always @(posedge clk)
            for (int i = 0; i < W; i++)
                if (!rst_local[i / RG]) r[i] <= 1'b0;
`ifdef BF_SEAM_MUTANT_DATA
                else r[i] <= d[i] ^ (i == W/2);
`elsif BF_SEAM_MUTANT_SLOT
                else r[i] <= d[i] ^ (i == W-1);
`else
                else r[i] <= d[i];
`endif
        assign q = r;
    end else begin : g_direct
        assign q = d;
    end
endmodule
