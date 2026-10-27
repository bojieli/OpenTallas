`timescale 1ns/1ps
`default_nettype none
// Already-synchronous die reset: two ordinary timed regional edges preserve
// the host ingress legacy two-edge release. Assertion also takes two edges.
module ot_rst_delivered2 #(parameter integer REGIONS=1)(
 input wire clk,rst_n_in,output wire[REGIONS-1:0]rst_n
);
 for(genvar r=0;r<REGIONS;r=r+1)begin:g_region
  (* keep=1,dont_touch=1 *) reg[1:0]pipe;
  always @(posedge clk)pipe<={pipe[0],rst_n_in};
  assign rst_n[r]=pipe[1];
 end
endmodule
`default_nettype wire
