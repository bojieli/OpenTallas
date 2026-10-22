`timescale 1ns/1ps
`default_nettype none
// Unreset fixed delay (L2H-IDXSCORE 2026-10-19, SAFE checklist item 5): D <= 2 -> ot_hdc_delay shift stages, D >= 3 ->
// ot_hdc_delay_rf ring buffer (cycle-exact, data unreset as RESET = 0), so no >= 3-deep zero-logic flop->flop hold chain.
module ot_hdc_delay_auto #(
    parameter integer W = 32,
    parameter integer D = 1
) (
    input  wire         clk,
    input  wire [W-1:0] d,
    output wire [W-1:0] q
);
    generate
        if (D >= 3) begin : g_rf
            ot_hdc_delay_rf #(.W(W), .D(D)) u (.clk(clk), .rst_n(1'b1), .d(d), .q(q));
        end else begin : g_sh
            ot_hdc_delay #(.W(W), .D(D)) u (.clk(clk), .rst_n(1'b1), .d(d), .q(q));
        end
    endgenerate
endmodule
`default_nettype wire
