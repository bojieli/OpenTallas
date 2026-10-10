`timescale 1ns/1ps
// mtp-hbm 2026-10-08: registered valid/ready slice for a die-block pin boundary (template D).
// in_ready, out_v and out_d all come straight from flops; a 2-entry skid absorbs the one beat that arrives while
// out_ready is low.  Transaction-exact: same beats, same order, +1 cycle.
module ot_hfd_mtp_skid #(parameter integer W = 8) (
    input  wire         clk,
    input  wire         rst_n,
    input  wire         in_v,
    output reg          in_ready,
    input  wire [W-1:0] in_d,
    output reg          out_v,
    input  wire         out_ready,
    output reg  [W-1:0] out_d
);
    reg         s_v;
    reg [W-1:0] s_d;
    wire in_fire = in_v && in_ready;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin out_v <= 1'b0; s_v <= 1'b0; in_ready <= 1'b0; end
        else begin
            if (!out_v || out_ready) begin
                if (s_v) begin out_v <= 1'b1; s_v <= 1'b0; end
                else out_v <= in_fire;
            end else if (in_fire) s_v <= 1'b1;
            // registered ready: room for one more beat after this edge
            in_ready <= (!out_v || out_ready) || !(s_v || in_fire);
        end
    end
    always @(posedge clk) begin
        if (!out_v || out_ready) out_d <= s_v ? s_d : in_d;
        if (!s_v && out_v && !out_ready && in_fire) s_d <= in_d;
    end
endmodule
