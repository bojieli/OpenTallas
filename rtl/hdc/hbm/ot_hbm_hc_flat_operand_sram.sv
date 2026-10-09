`timescale 1ns/1ps
// Natural-order BF16 residual snapshot -> private8term banks.16 paired BF16
// lanes/word each protected independently with32+7SECDED. Three256b real
// macros/bank pack624live bits, with active-high partial writes, noRMW.
// ReadML3. Rowlease mustmatchcommand;1280unique beats mustCOMMIT before ready.
// LEASE_CHECK (cont-takeover 2026-10-09): 0 drops the row-lease identity compare (REVIEW S3 binding: fn/x rows are a
// fixed-order snapshot; ordering comes from start/release and the per-beat seen map, which stay).  Default 1 = unchanged.
module ot_hbm_hc_flat_operand_sram #(parameter integer LEASE_CHECK=1)(
 input wire clk,rst_n,start,release_window,input wire[15:0]lease,
 input wire i_valid,output wire i_ready,input wire[15:0]i_lease,
 input wire[10:0]i_beat,input wire[255:0]i_data,
 output wire ready,input wire[7:0]re,input wire[127:0]addr,
 output wire[4095:0]q,output reg fault,output wire[127:0]ce_seen,ue_seen
);
 reg active,wr_v;reg[15:0]lease_r;reg[1279:0]seen;
 reg[10:0]committed;reg[6:0]wr_word;reg[3:0]wr_pair;
 wire bad=(LEASE_CHECK!=0 && i_lease!=lease_r) || i_beat>=1280 || seen[i_beat];
 wire accept=i_valid&&i_ready;
 assign i_ready=active&&!fault;
 assign ready=active&&!fault&&(committed==1280)&&!wr_v;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin active<=0;wr_v<=0;seen<=0;committed<=0;fault<=0;lease_r<=0;end
  else begin
   wr_v<=accept&&!bad;
   if(accept)begin
    if(bad)fault<=1;
    else begin seen[i_beat]<=1;wr_word<=i_beat[10:4];wr_pair<=i_beat[3:0];end
   end
   if(wr_v)committed<=committed+1'b1;
   if(start)begin
    if(active)fault<=1;
    else begin active<=1;lease_r<=lease;seen<=0;committed<=0;end
   end
   if(release_window)begin if(!ready)fault<=1;else active<=0;end
   if(|ue_seen)fault<=1;
   for(integer b=0;b<8;b=b+1)if(re[b]&&(!ready || addr[b*16+:16]>=80))fault<=1;
  end
 end
 genvar b,m,p;generate for(b=0;b<8;b=b+1)begin:bank
  wire[38:0]code;
  ot_secded_enc #(.K(32),.R(7))enc(.clk(clk),.d({i_data[(b+8)*16+:16],i_data[b*16+:16]}),.q(code));
  wire[767:0]write_data=({729'd0,code}<<(wr_pair*39));
  wire[767:0]write_mask=({729'd0,39'h7fffffffff}<<(wr_pair*39));
  wire[767:0]raw;reg rv;
  always @(posedge clk or negedge rst_n)if(!rst_n)rv<=0;else rv<=re[b]&&ready;
  for(m=0;m<3;m=m+1)begin:ram
   ot_sram_1r1w_128x256_m1_r2c2 sram(.clk(clk),.r_ce_in(re[b]&&ready),.r_addr_in(addr[b*16+:7]),.rd_out(raw[m*256+:256]),
    .w_ce_in(wr_v&&(|write_mask[m*256+:256])),.w_addr_in(wr_word),.wd_in(write_data[m*256+:256]),.w_mask_in(write_mask[m*256+:256]),
    .rr_en(2'b0),.rr_addr(14'd0),.cr_en(2'b0),.cr_sel(16'd0));
  end
  for(p=0;p<16;p=p+1)begin:pair
   wire[31:0]d;wire ov;
   ot_secded_dec #(.K(32),.R(7))dec(.clk(clk),.rst_n(rst_n),.v(rv),.w(raw[p*39+:39]),
    .ov(ov),.d(d),.ce(ce_seen[b*16+p]),.ue(ue_seen[b*16+p]),.n_ce(),.n_ue());
   assign q[(b*16+p)*32+:32]=ue_seen[b*16+p]?32'd0:d;
  end
 end endgenerate
endmodule
