`timescale 1ns/1ps
`default_nettype none
// Already-synchronous die reset: three timed regional relay edges preserve the
// legacy two-sync-plus-one-tree RELEASE date. Assertion also takes three edges.
// Boot/START waits for all delivered offsets and nested local relay depths.
// These paths receive ordinary timing; there is no local CDC or false path.
module ot_rst_delivered3 #(parameter integer REGIONS=4)(
 input wire clk,rst_n_in,
 output wire[REGIONS-1:0]rst_n
);
 for(genvar r=0;r<REGIONS;r=r+1)begin:g_region
  (* keep=1,dont_touch=1 *) reg[2:0]pipe;
  always @(posedge clk)pipe<={pipe[1:0],rst_n_in};
  assign rst_n[r]=pipe[2];
 end
endmodule
`default_nettype wire
