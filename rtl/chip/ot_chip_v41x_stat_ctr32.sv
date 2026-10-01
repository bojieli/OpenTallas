`timescale 1ns/1ps
// ot_chip_v41x_stat_ctr32 -- a 32-bit event counter split into two 16-bit halves with a registered carry
// (W18b, 1.2 GHz sign-off of the K-arb root: the plain 32-bit increment was its SS-critical path, -142 ps).
// q is the exact running total ONE cycle late (q(t+1) = total through cycle t): the low half is delayed a cycle
// to line up with the high half, which absorbs the registered carry.  Statistics outputs only.
module ot_chip_v41x_stat_ctr32 #(
    parameter integer IW = 8              // increment width
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [IW-1:0] inc,
    output wire [31:0]   q
);
    reg [15:0] lo, lo_d, hi;
    reg        cy;
    wire [16:0] s = {1'b0, lo} + 17'(inc);
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin lo <= '0; lo_d <= '0; hi <= '0; cy <= 1'b0; end
        else begin
            lo   <= s[15:0];
            cy   <= s[16];
            lo_d <= lo;
            hi   <= hi + 16'(cy);
        end
    assign q = {hi, lo_d};
endmodule
