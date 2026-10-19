`timescale 1ns/1ps
// PRIVATE functional source only. No current die binding or physical receipt.
// Exact 11 existing transport edges. 565 live bits, no padding or reset.
module ot_kv_z17_shard188_private(input wire ck,input wire [187:0] a,output reg [187:0] b);
 always @(posedge ck) b<=a;
endmodule
module ot_kv_z17_shard189_private(input wire ck,input wire [188:0] a,output reg [188:0] b);
 always @(posedge ck) b<=a;
endmodule
module ot_kv_z17_transport_private(input wire ck,input wire [547:0] payload_in,input wire [16:0] zero_in,
 output wire [547:0] payload_out,output wire [16:0] zero_out);
 wire [564:0] cohort[0:11];
 assign cohort[0]={zero_in,payload_in};
 genvar k;
 generate for(k=0;k<11;k=k+1)begin:g_hop
 ot_kv_z17_shard188_private a(.ck(ck),.a(cohort[k][187:0]),.b(cohort[k+1][187:0]));
 ot_kv_z17_shard188_private b(.ck(ck),.a(cohort[k][375:188]),.b(cohort[k+1][375:188]));
 ot_kv_z17_shard189_private c(.ck(ck),.a(cohort[k][564:376]),.b(cohort[k+1][564:376]));
 end endgenerate
 assign {zero_out,payload_out}=cohort[11];
endmodule
