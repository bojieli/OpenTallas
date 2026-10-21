`timescale 1ns/1ps
// Fixed-calendar bridge from one DV beat leaf's 256b VM extension to the
// existing production D512 KV bank. One bank per die at s_3N leaf0, opt-in.
// Opcode15: a0=parameter row base, a1=operand row base, n=32;
// imm kind[3:0] (KV1/GK7),gain[5:4],jid[13:6],DRAIN_AGE[31:16].
// Two VM pair responses form one512b spine row on slot0; all other slots idle.
// Exactly26 KV events are stored independently, including both exponent masks.
// Output SRAM:16 banks x9 x32x64 hard macros, two occupied rows per bank.
// Drain uses four edges/event (read, latch, low256, high256),104edges total.
// DRAIN_AGE must be measured and priced by the compiler; no ready-driven issue.
module ot_s81sl_kv_leaf (
 input wire clk,rst_n,input wire c_v,input wire [159:0] c_d,
 output reg busy,done,output reg fault,
 output reg x_rv,output reg [9:0] x_ra,input wire x_qv,input wire [255:0] x_qd,
 output reg x_wv,output reg [9:0] x_wa,output reg [7:0] x_wm,output reg [255:0] x_wd
);
 wire start=c_v && c_d[3:0]==15;
 wire [127:0] imm=c_d[159:32];
 reg [15:0] age,drain_age;reg [9:0] pbase,ibase;
 reg [7:0] issued,received;reg [7:0] npairs;reg [3:0] kind;
 reg dn_st;reg [1:0] gsel;reg [7:0] jid;
 reg [15:0] dn_v;reg [8191:0] dn_d;reg [255:0] halfrow;
 wire [15:0] ov;wire [223:0] oa;wire [255:0] om;wire [8191:0] od;
 wire bf,bon,bid;
 ot_s81sl_kv_bank u_bank(.sk(clk),.rst_n(rst_n),.dn_st(dn_st),.dn_kind(kind),.dn_gsel(gsel),.dn_jid(jid),
 .dn_v(dn_v),.dn_d(dn_d),.wq_v(ov),.wq_row(oa),.wq_mask(om),.wq_d(od),.fault(bf),.online(bon),.input_done(bid));
 reg [1:0] count[0:15];
 reg [3:0] bank;reg entry;reg [1:0] phase;reg draining;reg finishing;
 wire [575:0] rd[0:15];reg [575:0] packet;
 genvar b,w;
 generate for(b=0;b<16;b=b+1)begin:g_store
  wire [575:0] wd={34'd0,oa[14*b+:14],om[16*b+:16],od[512*b+:512]};
  for(w=0;w<9;w=w+1)begin:g_word
   ot_sram_1r1w2c_32x64_m1 u_m(.wclk(clk),.rclk(clk),
    .w_ce_in(busy && ov[b] && count[b]<2),.w_addr_in({3'd0,count[b]}),.wd_in(wd[64*w+:64]),.w_mask_in(64'hffffffffffffffff),
    .r_ce_in(draining && phase==0 && bank==b),.r_addr_in({4'd0,entry}),.rd_out(rd[b][64*w+:64]));
  end
 end endgenerate
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   busy<=0;done<=0;fault<=0;dn_st<=0;dn_v<=0;x_rv<=0;x_wv<=0;
   age<=0;drain_age<=0;issued<=0;received<=0;npairs<=0;kind<=0;gsel<=0;jid<=0;
   bank<=0;entry<=0;phase<=0;draining<=0;finishing<=0;
   for(i=0;i<16;i=i+1)count[i]<=0;
  end else begin
   done<=0;dn_st<=0;dn_v<=0;x_rv<=0;x_wv<=0;
   if(bf)fault<=1;
   if(c_v && busy)fault<=1;
   if(start && !busy)begin
    // No generic opcode fallback; unsupported kind/shape or impossible calendar
    // fails visibly, rather than silently running a different norm shape.
    if((imm[3:0]!=1 && imm[3:0]!=7)||c_d[31:24]!=32||imm[31:16]<128 ||
       c_d[5:4]!=0 || c_d[15:14]!=0 || c_d[23:14]>896 ||
       c_d[13:4]>(imm[3:0]==1?1004:1020) || imm[127:32]!=0 || imm[15:14]!=0)fault<=1;
    else begin
     busy<=1;age<=0;drain_age<=imm[31:16];pbase<=c_d[13:4];ibase<=c_d[23:14];
     issued<=0;received<=0;npairs<=imm[3:0]==1?74:66;kind<=imm[3:0];gsel<=imm[5:4];jid<=imm[13:6];dn_st<=1;
     bank<=0;entry<=0;phase<=0;draining<=0;finishing<=0;
     for(i=0;i<16;i=i+1)count[i]<=0;
    end
   end
   if(busy)begin
    age<=age+1;
    if(finishing)begin busy<=0;done<=1;finishing<=0;end
    if(issued<npairs)begin
     x_rv<=1;
     x_ra<=issued<(kind==1?10:2)?pbase+2*issued:ibase+2*(issued-(kind==1?10:2));
     issued<=issued+1;
    end
    if(x_qv)begin
     if(received>=npairs)fault<=1;
     else begin
      if(!received[0])halfrow<=x_qd;
      else begin dn_v<=16'h0001;dn_d<={7680'd0,x_qd,halfrow};end
      received<=received+1;
     end
    end
    for(i=0;i<16;i=i+1)if(ov[i])begin
     // Witness the in-place input/output lifetime obligation.
     if(received!=npairs || draining || count[i]>=2)fault<=1;
     count[i]<=count[i]+1;
    end
    if(age==drain_age)begin
     if(received!=npairs)fault<=1;
     if(kind==7)begin busy<=0;done<=1;end
     else begin draining<=1;bank<=0;entry<=0;phase<=0;end
    end
    if(draining)begin
     phase<=phase+1;
     if(phase==0 && count[bank]!=(bank[0]==0 || bank[2:0]==7?2:1))fault<=1;
     if(phase==1)packet<=rd[bank];
     if(phase==2 || phase==3)begin
      if(packet[541:528]>255)fault<=1;
      x_wv<=1;x_wa<={packet[535:528],2'b00}+(phase==3?2:0);
      x_wm<=phase==2?packet[519:512]:packet[527:520];
      x_wd<=phase==2?packet[255:0]:packet[511:256];
     end
     if(phase==3)begin
      if(!entry && (bank[0]==0 || bank[2:0]==7))entry<=1;
      else if(bank==15)begin draining<=0;finishing<=1;end
      else begin bank<=bank+1;entry<=0;end
     end
    end
   end else if(|ov)fault<=1;
  end
 end
endmodule
