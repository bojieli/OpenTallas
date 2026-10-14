`timescale 1ns/1ps
`default_nettype none
// Pure explicit protocol translation. Burst owner MUST retain sid/mirror until
// all request credits and responses drain. Client configured W8LQ10 (RRS3).
// Existing xload command bases must be rebased into the validated local offset.
module ot_hbm_b2_xread_aperture #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire permit,input wire [1:0] sid,input wire mirror,
 input wire [32*16-1:0] old_q,output wire [31:0] old_cr,
 output wire [32*257-1:0] old_rsp,
 output wire [8*17-1:0] rq,input wire [7:0] rq_cr,input wire [8*257-1:0] rr,
 output reg fault
);
 wire [7:0] bad;
 wire [23:0] upper_v;
 for(genvar u=0;u<24;u=u+1)begin:unused_lane
  assign upper_v[u]=old_q[(u+8)*16+15];
 end
 wire unused=|upper_v;
 for(genvar b=0;b<8;b=b+1)begin:lane
  wire [15:0] q=old_q[b*16+:16];
  // Owned offset is13 sector bits; mirror has12 valid offset sector bits.
  assign bad[b]=q[15]&&(q[14:13]!=0||(mirror&&q[12]));
  assign rq[b*17+:17]={q[15]&&permit&&!fault&&!unused&&!(|bad),mirror,mirror?2'b00:(MUT==1?sid^2'b01:sid),q[12:0]};
  assign old_cr[b]=rq_cr[b];
  assign old_rsp[b*257+:257]=rr[b*257+:257];
 end
 assign old_cr[31:8]=0;assign old_rsp[32*257-1:8*257]=0;
 always @(posedge clk or negedge rst_n)
  if(!rst_n)fault<=0;
  else if(unused||(|bad)||(!permit&&(|{old_q[127],old_q[111],old_q[95],old_q[79],old_q[63],old_q[47],old_q[31],old_q[15]})))fault<=1;
endmodule
`default_nettype wire
