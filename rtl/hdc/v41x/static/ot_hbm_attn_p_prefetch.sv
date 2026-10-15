`timescale 1ns/1ps
`default_nettype none
// Source-format-preserving P gather. Head-major FP32 nativeVM words must lie
// on the BF16 grid. Read returns fourrows x16heads in exactPWORDS2 load order.
module ot_hbm_attn_p_prefetch #(
 parameter integer FILL_LAT=8
)(
 input wire clk,rst_n,
 input wire fetch_v,fetch_epoch,input wire[3:0]fetch_head,fetch_burst,
 input wire[15:0]fetch_base_sector,profile_rows,
 output reg[135:0]rq,input wire[2055:0]rr,
 input wire read_v,read_epoch,input wire[9:0]read_row,
 output reg p_v,output wire[1023:0]p_w,output reg fault
);
 reg[FILL_LAT-1:0]vp,ep;
 reg[3:0]hp[0:FILL_LAT-1],bp[0:FILL_LAT-1];
 reg[2:0]bank_q,offset_q;
 wire[127:0]words[0:127];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
  rq<=0;vp<=0;ep<=0;p_v<=0;fault<=0;bank_q<=0;offset_q<=0;
 end else begin
  rq<=0;vp<={vp[FILL_LAT-2:0],fetch_v};ep<={ep[FILL_LAT-2:0],fetch_epoch};p_v<=read_v;
  if(read_v)begin bank_q<=read_row[5:3];offset_q<=read_row[2:0];end
  for(integer b=0;b<8;b=b+1)begin
   rq[b*17+:17]<={fetch_v,16'(fetch_base_sector+b)};
   if(rr[b*257+256]!=vp[FILL_LAT-1])fault<=1;
   if(vp[FILL_LAT-1])for(integer w=0;w<8;w=w+1)
    if(rr[b*257+w*32+:16]!=0)fault<=1;
  end
  if(fetch_v&&(fetch_base_sector[2:0]!=0||fetch_burst>=((profile_rows+63)/64)))fault<=1;
  if((fetch_v||read_v)&&!(profile_rows==128||profile_rows==640))fault<=1;
  if(read_v&&(read_row[1:0]!=0||{6'd0,read_row}+16'd3>=profile_rows))fault<=1;
 end
 always @(posedge clk)begin
  hp[0]<=fetch_head;bp[0]<=fetch_burst;
  for(integer i=1;i<FILL_LAT;i=i+1)begin hp[i]<=hp[i-1];bp[i]<=bp[i-1];end
 end
 genvar s,w,h,r;
 generate for(s=0;s<128;s=s+1)begin:g_store
  localparam integer HEAD=s/8,BANK=s%8;
  wire[127:0]wd;
  for(w=0;w<8;w=w+1)begin:g_word
   assign wd[w*16+:16]=rr[BANK*257+w*32+16+:16];
  end
  ot_sram_1r1w_32x128_m1 u_mem(.clk(clk),.r_ce_in(read_v&&read_row[5:3]==3'(BANK)),
   .r_addr_in({read_epoch,read_row[9:6]}),.rd_out(words[s]),
   .w_ce_in(vp[FILL_LAT-1]&&hp[FILL_LAT-1]==4'(HEAD)),.w_addr_in({ep[FILL_LAT-1],bp[FILL_LAT-1]}),
   .wd_in(wd),.w_mask_in({128{1'b1}}));
 end
 for(h=0;h<16;h=h+1)begin:g_head
  for(r=0;r<4;r=r+1)begin:g_row
   assign p_w[(r*16+h)*16+:16]=words[h*8+bank_q][(int'(offset_q)+r)*16+:16];
  end
 end endgenerate
endmodule
`default_nettype wire
