`timescale 1ns/1ps
`default_nettype none
// Source-preserving NL2/H16 QK score store. Exactly sixteen masked 64-bit
// writes and sixteen 128-bit reads use real independent 1R1W macro ports.
// All requests are compiled inputs; observations only latch faults.
module ot_hbm_attn_qk_score_serializer(
 input wire clk,rst_n,
 input wire capture_v,capture_epoch,capture_T640,
 input wire[15:0]capture_row,input wire[1:0]capture_mask,
 input wire[1023:0]capture_data,input wire[31:0]capture_flags,
 input wire drain_v,drain_epoch,drain_T640,
 input wire[3:0]drain_head,drain_block,
 input wire[15:0]drain_base_sector,
 output reg write_v,output wire[2047:0]write_data,
 output wire[63:0]write_flags,output reg[15:0]write_base_sector,
 output reg fault
);
 wire[127:0]bq[0:255];wire[3:0]fq[0:255];
 reg[3:0]head_q;reg[9:0]rows_seen[0:1];reg kind[0:1];
 genvar b,a,d;
 generate for(b=0;b<256;b=b+1)begin:g_bank
  localparam integer H=b/16,S=b%16;
  wire we=capture_v&&capture_row[5:2]==4'(S);
  wire[127:0]wd={64'd0,capture_data[(16+H)*32+:32],capture_data[H*32+:32]} << (capture_row[1]*64);
  wire[63:0]lane_mask={{32{capture_mask[1]}},{32{capture_mask[0]}}};
  wire[127:0]wm={64'd0,lane_mask} << (capture_row[1]*64);
  wire re=drain_v&&drain_head==4'(H);
  wire[4:0]wa={capture_epoch,capture_row[9:6]},ra={drain_epoch,drain_block};
  ot_sram_1r1w_32x128_m1 u_data(.clk(clk),.r_ce_in(re),.r_addr_in(ra),.rd_out(bq[b]),
   .w_ce_in(we),.w_addr_in(wa),.wd_in(wd),.w_mask_in(wm));
  // Exact status bits are explicit flops, not a behavioral payload array.
  wire[127:0]flags_by_addr;
  for(a=0;a<32;a=a+1)begin:g_flags
   reg[3:0]f;integer l;
   always @(posedge clk)if(we&&wa==5'(a))begin
    for(l=0;l<2;l=l+1)if(capture_mask[l])f[int'(capture_row[1])*2+l]<=capture_flags[l*16+H];
   end
   assign flags_by_addr[a*4+:4]=f;
  end
  reg[3:0]fr;always @(posedge clk)if(re)fr<=flags_by_addr[ra*4+:4];
  assign fq[b]=fr;
 end
 for(d=0;d<64;d=d+1)begin:g_out
  assign write_data[d*32+:32]=bq[int'(head_q)*16+d/4][(d%4)*32+:32];
  assign write_flags[d]=fq[int'(head_q)*16+d/4][d%4];
 end endgenerate
 integer e;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  write_v<=0;write_base_sector<=0;head_q<=0;fault<=0;
  for(e=0;e<2;e=e+1)begin rows_seen[e]<=0;kind[e]<=0;end
 end else begin
  write_v<=drain_v;
  if(capture_v)begin
   if(capture_mask!=2'b11||capture_row[0]||capture_row>=(capture_T640?640:128))fault<=1;
   if(capture_row==0)begin rows_seen[capture_epoch]<=2;kind[capture_epoch]<=capture_T640;end
   else begin
    if(capture_row!=rows_seen[capture_epoch]||kind[capture_epoch]!=capture_T640)fault<=1;
    rows_seen[capture_epoch]<=10'(capture_row+2);
   end
  end
  if(drain_v)begin
   head_q<=drain_head;
   write_base_sector<=drain_base_sector+16'(int'(drain_head)*(drain_T640?80:16)+int'(drain_block)*8);
   if(drain_block>=(drain_T640?10:2)||kind[drain_epoch]!=drain_T640||
      rows_seen[drain_epoch]<(int'(drain_block)+1)*64||drain_base_sector[2:0]!=0)fault<=1;
   if(capture_v&&capture_epoch==drain_epoch&&capture_row[9:6]==drain_block)fault<=1;
  end
 end
endmodule
`default_nettype wire
