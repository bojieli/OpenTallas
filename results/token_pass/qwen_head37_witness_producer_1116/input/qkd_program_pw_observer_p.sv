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
 // CTLM8: at most one effective <=> no effective slice has a later one (no 16-b decrement chain)
 wire one=(|eff)&&((eff&later)==16'd0);
 // CTLM8: AND-OR selects as per-bit reduction trees (the serial OR accumulation mapped to a 16-deep AO21 chain)
 wire [15:0] col_d [0:63];
 wire [15:0] col_a [0:9];
 genvar b,k;
 generate for(b=0;b<64;b=b+1)begin:g_cd
  for(k=0;k<16;k=k+1)begin:g_k assign col_d[b][k]=pick[k]&macro_data[64*k+b]; end
 end endgenerate
 generate for(k=0;k<16;k=k+1)begin:g_ca
  wire [9:0] av={macro_row[6*(k/8) +:6],1'(k/8),3'(k%8)};
  for(b=0;b<10;b=b+1)begin:g_b assign col_a[b][k]=pick[k]&av[b]; end
 end endgenerate
 integer i;
 always @* begin
  for(i=0;i<64;i=i+1)consumed_data[i]=|col_d[i];
  for(i=0;i<10;i=i+1)consumed_addr[i]=|col_a[i];
  full_word=(macro_ce!=2'b11)&&one&&((eff&~ful)==16'd0);
 end
endmodule
