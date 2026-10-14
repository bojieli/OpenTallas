`timescale 1ns/1ps
// Local mutable state. Cold POR is the only erase path. Complementary state
// detects an upset before its owner/valid/pointer may authorize a transaction.
// Separate kept hierarchy is mandatory; mapped retention is a physical gate.
(* keep_hierarchy = "yes" *)
module ot_qwen_s4_checked_state #(
    parameter integer W = 1,
    parameter [W-1:0] INIT = {W{1'b0}}
) (
    input wire clk, por_n, en,
    input wire [W-1:0] d,
    output wire [W-1:0] q,
    output wire [W-1:0] qi,
    output wire bad
);
    (* keep, dont_touch *) reg [W-1:0] primary;
    (* keep, dont_touch *) reg [W-1:0] inverse;
    assign q = primary;
    assign qi = inverse;
    assign bad = |(primary ^ ~inverse);
    always @(posedge clk or negedge por_n)
        if (!por_n) begin primary <= INIT; inverse <= ~INIT; end
        else if (en && !bad) begin primary <= d; inverse <= ~d; end
endmodule
