`timescale 1ns/1ps
// Dedicated KV CDC fault observation relay: one core edge; no payload scheduling.
module qkd_kv_fault_stage(input wire ck, input wire [0:0] a, output reg [0:0] b);
    always @(posedge ck) b <= a;
endmodule
