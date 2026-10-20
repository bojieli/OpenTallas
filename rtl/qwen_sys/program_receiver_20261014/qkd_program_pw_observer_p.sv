`timescale 1ns/1ps
// CTLM7 (2026-10-20): depth-safe twin of qkd_program_pw_observer (identical ports and
// combinational function, bit-exact incl. multi-slice / both-bank cases).  The original
// is a serial loop: 16 x (32-bit count+1, priority overwrite of addr/data), 75 levels
// (u_gi.u_cal.u_obs.count -> full_word).  Here every slice is decoded in parallel:
// eff[i] = bank enabled & mask!=0, last-wins one-hot select (i = 8*bank + slice, the loop
// order), exactly-one = one-hot check, and AND-OR data/addr muxes.  Still combinational
// (the ledger samples it on the same edge the macros consume it): 0 added edges.
module qkd_program_pw_observer_p(
 input wire [1:0] macro_ce,input wire [11:0] macro_row,
 input wire [1023:0] macro_data,macro_mask,
 output wire consumed_v,output reg [9:0] consumed_addr,
 output reg [63:0] consumed_data,output reg full_word);
 assign consumed_v=|macro_ce;
 wire [15:0] eff,ful;
 genvar g;
 generate for(g=0;g<16;g=g+1)begin:g_s
  assign eff[g]=macro_ce[g/8]&&(|macro_mask[64*g +:64]);
  assign ful[g]=&macro_mask[64*g +:64];
 end endgenerate
 // last-wins: slice i is selected when it is effective and no later slice is
 wire [15:0] later;
 assign later[15]=1'b0;
 generate for(g=0;g<15;g=g+1)begin:g_l
  assign later[g]=|eff[15:g+1];
 end endgenerate
 wire [15:0] pick=eff&~later;
 // exactly one effective slice: none later than the picked one and none earlier
 wire one=(|eff)&&((eff&(eff-16'd1))==16'd0);
 integer i;
 always @* begin
  consumed_addr=0;consumed_data=0;
  for(i=0;i<16;i=i+1)begin
   consumed_addr=consumed_addr|({10{pick[i]}}&{macro_row[6*(i/8) +:6],1'(i/8),3'(i%8)});
   consumed_data=consumed_data|({64{pick[i]}}&macro_data[64*i +:64]);
  end
  full_word=(macro_ce!=2'b11)&&one&&((eff&~ful)==16'd0);
 end
endmodule
