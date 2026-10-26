`timescale 1ns/1ps
`default_nettype none
// One actual hardened-leaf candidate: flatten this wrapper with native replay
// implementation; all incoming faces capture at pins, including macro address.
module ot_hgi_coll_static_pinreg_store #(parameter integer MUT=0)(
 input wire clk,we,input wire [5:0] wa,ra,input wire [140:0] din,
 output wire [140:0] dout
);
 reg we_pin;reg [5:0] wa_pin,ra_pin;reg [140:0] din_pin;
 always @(posedge clk)begin
  we_pin<=we;wa_pin<=wa;ra_pin<=ra;din_pin<=din;
 end
 ot_qkvd_llr_replay_sram_leaf #(.W(141),.MUT(MUT)) u_native(
 .ck(clk),.we(we_pin),.wa(wa_pin),.ra(ra_pin),.din(din_pin),.dout(dout));
endmodule
`default_nettype wire
