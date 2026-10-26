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
//
// RTLGAP-SUKV 10-21 (G-L2-L20-HW), two opt-in parameters, both 0 by default (= the KV1/GK7 bridge above, unchanged):
//  CNIK=1  kinds 12 CN (compressor row, D512) and 13 IK (index key, D128) on the same bank (ot_s81sl_kv_bank CNIK=1).
//          Same command and calendar as KV: 10 parameter pairs (descriptor {eps[127:96], nbase[77:64], obase[13:0]},
//          cos lo/hi, sin lo/hi) + 64 operand pairs (32 rows of 16 FP32).  IK: operand rows 0..23 must be ZERO (the
//          hub contract: the D128 key sits on KVE48..63; a nonzero prefix word is a sticky fault).  Events a bank:
//          CN 3 (norm row nbase+b, QDQ row obase+b, raw codes/scales row obase+16+b), IK 2 on banks 0..3 (QDQ obase+b,
//          raw obase+4+b): CN 48 events / 192 drain edges, IK 8 / 32.
//  CP=1    kind 14 CP: the compressor gate-softmax pool (ot_s81sl_cmp_pool, its own fixed calendar on this port):
//          a0 = slot-0 (older) record base, a1 = slot-1 record base, n = 32, imm[13:4] = output base, rest 0.
// The leaf runs one job at a time (busy covers both engines); a command while busy is a sticky fault.
module ot_s81sl_kv_leaf #(
 parameter integer CNIK=0, CP=0, HARD_RQ=0, CP_MUT=0, CNIK_MUT=0
)(
 input wire clk,rst_n,input wire c_v,input wire [159:0] c_d,
 output reg busy,done,output reg fault,
 output reg x_rv,output reg [9:0] x_ra,input wire x_qv,input wire [255:0] x_qd,
 output reg x_wv,output reg [9:0] x_wa,output reg [7:0] x_wm,output reg [255:0] x_wd
);
 localparam [3:0] K_KV=1,K_GK=7,K_CN=12,K_IK=13,K_CP=14;
 wire start=c_v && c_d[3:0]==15;
 wire [127:0] imm=c_d[159:32];
 wire [3:0] ck=imm[3:0];
 wire is_cn=(CNIK!=0)&&(ck==K_CN), is_ik=(CNIK!=0)&&(ck==K_IK), is_cp=(CP!=0)&&(ck==K_CP);
 wire norm_kind=(ck==K_KV)||is_cn||is_ik;                         // 5 parameter rows + 32 operand rows
 // the bank engine (KV / GK / CN / IK)
 reg kbusy,kdone,kfault;
 reg kx_rv;reg [9:0] kx_ra;reg kx_wv;reg [9:0] kx_wa;reg [7:0] kx_wm;reg [255:0] kx_wd;
 reg [15:0] age,drain_age;reg [9:0] pbase,ibase;
 reg [7:0] issued,received;reg [7:0] npairs;reg [3:0] kind;
 reg dn_st;reg [1:0] gsel;reg [7:0] jid;
 reg [15:0] dn_v;reg [8191:0] dn_d;reg [255:0] halfrow;
 wire [15:0] ov;wire [223:0] oa;wire [255:0] om;wire [8191:0] od;
 wire bf,bon,bid;
 ot_s81sl_kv_bank #(.CNIK(CNIK),.HARD_RQ(HARD_RQ),.CNIK_MUT(CNIK_MUT)) u_bank(.sk(clk),.rst_n(rst_n),.dn_st(dn_st),.dn_kind(kind),.dn_gsel(gsel),.dn_jid(jid),
 .dn_v(dn_v),.dn_d(dn_d),.wq_v(ov),.wq_row(oa),.wq_mask(om),.wq_d(od),.fault(bf),.online(bon),.input_done(bid));
 reg [1:0] count[0:15];
 reg [3:0] bank;reg [1:0] entry;reg [1:0] phase;reg draining;reg finishing;
 wire [575:0] rd[0:15];reg [575:0] packet;
 // events a bank per kind (static): KV 2 on even banks and bank 7 / 15 else 1; CN 3; IK 2 on banks 0..3 else 0
 function automatic [1:0] nev(input [3:0] k,input [3:0] b);
  nev=(k==K_CN)?2'd3:(k==K_IK)?((b<4)?2'd2:2'd0):((b[0]==0||b[2:0]==7)?2'd2:2'd1);
 endfunction
 wire [3:0] lastbank=(kind==K_IK)?4'd3:4'd15;
 genvar b,w;
 generate for(b=0;b<16;b=b+1)begin:g_store
  wire [575:0] wd={34'd0,oa[14*b+:14],om[16*b+:16],od[512*b+:512]};
  for(w=0;w<9;w=w+1)begin:g_word
   ot_sram_1r1w2c_32x64_m1 u_m(.wclk(clk),.rclk(clk),
    .w_ce_in(kbusy && ov[b] && count[b]<nev(kind,b)),.w_addr_in({3'd0,count[b]}),.wd_in(wd[64*w+:64]),.w_mask_in(64'hffffffffffffffff),
    .r_ce_in(draining && phase==0 && bank==b),.r_addr_in({3'd0,entry}),.rd_out(rd[b][64*w+:64]));
  end
 end endgenerate
 // IK zero prefix: operand pairs 0..47 (rows 0..23) after the 10 parameter pairs
 wire ik_prefix=(kind==K_IK)&&(received>=10)&&(received<58);
 integer i;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin
   kbusy<=0;kdone<=0;kfault<=0;dn_st<=0;dn_v<=0;kx_rv<=0;kx_wv<=0;
   age<=0;drain_age<=0;issued<=0;received<=0;npairs<=0;kind<=0;gsel<=0;jid<=0;
   bank<=0;entry<=0;phase<=0;draining<=0;finishing<=0;
   for(i=0;i<16;i=i+1)count[i]<=0;
  end else begin
   kdone<=0;dn_st<=0;dn_v<=0;kx_rv<=0;kx_wv<=0;
   if(bf)kfault<=1;
   if(c_v && kbusy)kfault<=1;
   if(start && !is_cp && !kbusy)begin
    // No generic opcode fallback; unsupported kind/shape or impossible calendar
    // fails visibly, rather than silently running a different norm shape.
    if((!norm_kind && ck!=K_GK)||c_d[31:24]!=32||imm[31:16]<128 ||
       c_d[5:4]!=0 || c_d[15:14]!=0 || c_d[23:14]>896 ||
       c_d[13:4]>(norm_kind?1004:1020) || imm[127:32]!=0 || imm[15:14]!=0)kfault<=1;
    else begin
     kbusy<=1;age<=0;drain_age<=imm[31:16];pbase<=c_d[13:4];ibase<=c_d[23:14];
     issued<=0;received<=0;npairs<=norm_kind?74:66;kind<=ck;gsel<=imm[5:4];jid<=imm[13:6];dn_st<=1;
     bank<=0;entry<=0;phase<=0;draining<=0;finishing<=0;
     for(i=0;i<16;i=i+1)count[i]<=0;
    end
   end
   if(kbusy)begin
    age<=age+1;
    if(finishing)begin kbusy<=0;kdone<=1;finishing<=0;end
    if(issued<npairs)begin
     kx_rv<=1;
     kx_ra<=issued<(kind!=K_GK?10:2)?pbase+2*issued:ibase+2*(issued-(kind!=K_GK?10:2));
     issued<=issued+1;
    end
    if(x_qv)begin
     if(received>=npairs)kfault<=1;
     else begin
      if(ik_prefix && x_qd!=0)kfault<=1;
      if(!received[0])halfrow<=x_qd;
      else begin dn_v<=16'h0001;dn_d<={7680'd0,x_qd,halfrow};end
      received<=received+1;
     end
    end
    for(i=0;i<16;i=i+1)if(ov[i])begin
     // Witness the in-place input/output lifetime obligation.
     if(received!=npairs || draining || count[i]>=nev(kind,i[3:0]))kfault<=1;
     count[i]<=count[i]+1;
    end
    if(age==drain_age)begin
     if(received!=npairs)kfault<=1;
     if(kind==K_GK)begin kbusy<=0;kdone<=1;end
     else begin draining<=1;bank<=0;entry<=0;phase<=0;end
    end
    if(draining)begin
     phase<=phase+1;
     if(phase==0 && count[bank]!=nev(kind,bank))kfault<=1;
     if(phase==1)packet<=rd[bank];
     if(phase==2 || phase==3)begin
      if(packet[541:528]>255)kfault<=1;
      kx_wv<=1;kx_wa<={packet[535:528],2'b00}+(phase==3?2:0);
      kx_wm<=phase==2?packet[519:512]:packet[527:520];
      kx_wd<=phase==2?packet[255:0]:packet[511:256];
     end
     if(phase==3)begin
      if(entry+2'd1<nev(kind,bank))entry<=entry+1;
      else if(bank==lastbank)begin draining<=0;finishing<=1;end
      else begin bank<=bank+1;entry<=0;end
     end
    end
   end else if(|ov)kfault<=1;
  end
 end
 // the pool engine (CP=1)
 wire pbusy,pdone,pfault,px_rv,px_wv;wire [9:0] px_ra,px_wa;wire [7:0] px_wm;wire [255:0] px_wd;
 generate if(CP!=0)begin:g_cp
  wire pstart=start && is_cp && !kbusy && !pbusy;
  wire pbad=start && is_cp && (c_d[31:24]!=32 || imm[127:14]!=0 || imm[3:0]!=K_CP);
  wire [255:0] y32;wire [15:0] pa;
  ot_s81sl_cmp_pool #(.MUT(CP_MUT)) u_pool(.clk(clk),.rst_n(rst_n),.start(pstart && !pbad),.b0(c_d[13:4]),.b1(c_d[23:14]),
   .ob(imm[13:4]),.busy(pbusy),.done(pdone),.fault(pfault),.x_rv(px_rv),.x_ra(px_ra),.x_qv(x_qv && pbusy),.x_qd(x_qd),
   .x_wv(px_wv),.x_wa(px_wa),.x_wm(px_wm),.x_wd(px_wd),.dbg_y32(y32),.dbg_age(pa));
  reg pcf;
  always @(posedge clk or negedge rst_n)if(!rst_n)pcf<=0;else if(pbad || (start && is_cp && (kbusy || pbusy)) ||
   (start && !is_cp && pbusy))pcf<=1;
  always @(*)begin
   busy=kbusy|pbusy;done=kdone|pdone;fault=kfault|pfault|pcf;
   x_rv=kx_rv|px_rv;x_ra=pbusy?px_ra:kx_ra;
   x_wv=kx_wv|px_wv;x_wa=pbusy?px_wa:kx_wa;x_wm=pbusy?px_wm:kx_wm;x_wd=pbusy?px_wd:kx_wd;
  end
 end else begin:g_nocp
  assign pbusy=0;assign pdone=0;assign pfault=0;assign px_rv=0;assign px_ra=0;assign px_wv=0;assign px_wa=0;
  assign px_wm=0;assign px_wd=0;
  always @(*)begin
   busy=kbusy;done=kdone;fault=kfault;x_rv=kx_rv;x_ra=kx_ra;x_wv=kx_wv;x_wa=kx_wa;x_wm=kx_wm;x_wd=kx_wd;
  end
 end endgenerate
endmodule
