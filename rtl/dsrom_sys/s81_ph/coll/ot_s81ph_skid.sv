`timescale 1ns/1ps
// ot_s81ph_skid (CLAUDE S81-PH, 2026-10-06): 2-slot skid buffer for latency-insensitive tile boundaries (DESIGN
// SIMPLIFICATION RULE 2).  out_v / out_d come from the main register, in_r from the skid-valid flop: no
// combinational path from in_* to out_* or from out_r to in_r.  Full throughput (one word a cycle).
module ot_s81ph_skid #(parameter integer W = 8) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_v,
    output wire         in_r,
    input  wire [W-1:0] in_d,
    output reg          out_v,
    input  wire         out_r,
    output reg  [W-1:0] out_d
);
    reg         sk_v;
    reg [W-1:0] sk_d;
    assign in_r = !sk_v;
    wire ld = out_r || !out_v;                 // main register free (or emptied this cycle)
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin out_v <= 1'b0; sk_v <= 1'b0; end
        else if (ld) begin
            if (sk_v) begin out_v <= 1'b1; sk_v <= 1'b0; end
            else out_v <= in_v;
        end else if (in_v && !sk_v) sk_v <= 1'b1;
    always @(posedge clk)
        if (ld) out_d <= sk_v ? sk_d : in_d;
        else if (in_v && !sk_v) sk_d <= in_d;
endmodule
