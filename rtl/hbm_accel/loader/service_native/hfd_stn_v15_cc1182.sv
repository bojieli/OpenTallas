`timescale 1ns/1ps
// H-DIE 2026-10-15: one common-clock relay stage of the SM_HBM link (service group -> SM): packet[1098:0] + command[82:0]
// = 1,182 bits, one stream-clock register stage (latency 1), same bit order in and out.  The die places R stages along
// the link at <= 480 um (reach rule); the compiler shifts every SM command and the SM's x-load issue by the same R.
module hfd_stn_v15_cc1182 (
    input  wire [1181:0] a,
    output reg  [1181:0] b,
    input  wire clk
);
    always @(posedge clk) b <= a;
endmodule
