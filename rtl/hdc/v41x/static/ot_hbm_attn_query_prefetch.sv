`timescale 1ns/1ps
`default_nettype none
// Fixed-slot FP32 VM query prefetch -> two physical BF16 query buffers.
// 64 actual 32x128 macros = two banks x16heads x512BF16; no inferred memory.
// Source precision matches ot_hgi_att_unit: FP32 sector word[31:16].
// FILL_LAT8: registered request1 + bare-bank response6 + consumer capture1.
// Add actual station edges to FILL_LAT; never wait for a returned valid.
module ot_hbm_attn_query_prefetch #(parameter integer FILL_LAT=8,MUT=0)(
 input wire clk,rst_n,
 input wire fetch_v,fetch_epoch,input wire [3:0]fetch_head,
 input wire [2:0]fetch_burst,input wire [15:0]fetch_base_sector,
 output reg [8*17-1:0]rq,input wire [8*257-1:0]rr,
 input wire read_v,read_epoch,input wire [3:0]read_head,
 output reg q_v,output wire [8191:0]q_w,output reg fault
);
 reg [FILL_LAT-1:0]vp,ep;
 reg [3:0]hp[0:FILL_LAT-1];reg[2:0]bp[0:FILL_LAT-1];
 integer i,b;
 always @(posedge clk or negedge rst_n) if(!rst_n)begin
  rq<=0;vp<=0;ep<=0;q_v<=0;fault<=0;
 end else begin
  vp<={vp[FILL_LAT-2:0],fetch_v};ep<={ep[FILL_LAT-2:0],fetch_epoch};q_v<=read_v;
  rq<=0;
  for(integer k=0;k<8;k=k+1)begin
   rq[k*17+:17]<={fetch_v,16'(fetch_base_sector+k)};
   if(rr[k*257+256]!=vp[FILL_LAT-1])fault<=1;
   // Native source contract rejects a non-BF16-grid FP32 operand. Preserve
   // upper16 extraction exactly, but never silently truncate nonzero lowbits.
   if(vp[FILL_LAT-1])for(integer w=0;w<8;w=w+1)
    if(rr[k*257+w*32+:16]!=16'd0)fault<=1;
  end
  if(fetch_v&&fetch_base_sector[2:0]!=0)fault<=1;
 end
 always @(posedge clk)begin
  hp[0]<=fetch_head;bp[0]<=fetch_burst;
  for(integer k=1;k<FILL_LAT;k=k+1)begin hp[k]<=hp[k-1];bp[k]<=bp[k-1];end
 end
 for(genvar s=0;s<64;s=s+1)begin:g_stripe
  localparam integer BANK=s%8,BURST=s/8;
  wire[127:0]wd,rd;
  for(genvar w=0;w<8;w=w+1)begin:g_word
   assign wd[w*16+:16]=rr[((BANK^(MUT==1?1:0))*257)+w*32+16+:16];
  end
  ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),
   .r_ce_in(read_v),.r_addr_in({read_epoch,read_head}),.rd_out(rd),
   .w_ce_in(vp[FILL_LAT-1]&&(bp[FILL_LAT-1]==BURST)),
   .w_addr_in({ep[FILL_LAT-1],hp[FILL_LAT-1]^(MUT==2?4'd1:4'd0)}),
   .wd_in(wd),.w_mask_in({128{1'b1}}));
  assign q_w[s*128+:128]=rd;
 end
 initial if(FILL_LAT<2)$fatal(1,"query-prefetch latency requires measured positive pipeline");
endmodule
`default_nettype wire
