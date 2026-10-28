`timescale 1ns/1ps
`default_nettype none
// Die-local prototype: payload only. Original station epochs/reset remain outside.
// One existing rising edge, no enable, reset, phase selector, or added latency.
(* keep_hierarchy, keep *)
module hbm_payload_bank256(input wire clk,input wire [255:0] d,output reg [255:0] q);
 always @(posedge clk) q<=d;
endmodule
(* keep_hierarchy, keep *)
module hbm_payload_bank1024(input wire clk,input wire [1023:0] d,output reg [1023:0] q);
 always @(posedge clk) q<=d;
endmodule
`default_nettype wire
