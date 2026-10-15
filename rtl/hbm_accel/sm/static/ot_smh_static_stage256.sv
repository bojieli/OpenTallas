`timescale 1ns/1ps
// One existing xwrite capture edge, hardened as an independent clock root.
// All256 payload bits are transported everyedge. Valid/control uses separate
// same-depth clock roots; payload reset is deliberately unnecessary.
module ot_smh_static_stage256 #(parameter integer MUT=0)(
 input wire clk,input wire [255:0] d,output reg [255:0] q
);
 always @(posedge clk) q<=d ^ ((MUT==1)?256'd1:256'd0);
endmodule
