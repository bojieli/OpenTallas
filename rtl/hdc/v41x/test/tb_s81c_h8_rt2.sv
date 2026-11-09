`timescale 1ns/1ps
// One native H8 head versus the same H8 behavioral head group. Actual CTLA
// sender and private timed reset are included. All32 dot-product lanes/order
// retained; only preselection of RT4 P columns differs. No physical claim.
module tb_s81c_h8_rt2;
 localparam H=8,TD=32,R=4;
 reg clk=0;always#0.5 clk=~clk;
 reg rst_n=0,ld_v=0,ld_mode=0,ld_w2v=0,iv=0;
 reg[2:0]ld_bank=0,ibank=0;reg[7:0]ld_grp=0;
 reg[1023:0]ld_w=0;reg[575:0]ib=0;
 wire lv,lm,l2;wire[2:0]lb;wire[7:0]lg;wire[1023:0]lw;
 ot_s81c_hcore_load_stage u_stage(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.out_v(lv),.out_mode(lm),.out_bank(lb),.out_grp(lg),.out_w(lw),.out_w2v(l2));
 integer gid_i=0,seed=1,mut=0,ncyc=16000;
 wire[7:0]gid=8'(gid_i);
 wire av,am,a2,af;wire[2:0]ab;wire[7:0]ag;wire[1023:0]aw;
 ot_s81c_h8_rt2_load expand_load(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.out_v(av),.out_mode(am),.out_bank(ab),.out_grp(ag),.out_w(aw),.out_w2v(a2),.fault(af));
 wire dv,dm,d2;wire[2:0]db;wire[7:0]dg;wire[1023:0]dw;
 ot_s81c_hcore_load_stage old_stage(.clk(clk),.rst_n(rst_n),.ld_v(av),.ld_mode(am),.ld_bank(ab),.ld_grp(ag),.ld_w(aw),.ld_w2v(a2),.out_v(dv),.out_mode(dm),.out_bank(db),.out_grp(dg),.out_w(dw),.out_w2v(d2));
 wire[63:0]wp;
 for(genvar w=0;w<2;w++)for(genvar j=0;j<2;j++)begin:pcols
  wire[7:0]h=(mut==1&&w==1)?8'((gid_i+1)%8):gid;
  assign wp[16*(2*w+j)+:16]=dw[w*512+16*(16*j+h)+:16];
 end
 reg re,rr;
 always@(posedge clk)begin re<=rst_n;rr<=re;end
 wire ro,d_o,rf,df;wire[31:0]ry,dy;
 ot_hdc_v41x_attn_hgrp_s #(.H(8),.HG(1),.TD(32),.NBANK(5),.BW(3),.PWORDS(2),.FPL(4),.FML(6),.F12(1),.PCOLP(0),.WPRE(2),.BZ0(1)) ref_h(
  .clk(clk),.rst_n(rr),.gid(gid),.ld_v(lv),.ld_mode(lm),.ld_bank(lb),.ld_grp(lg),.ld_w(lw),.ld_wp(128'd0),.ld_w2v(l2),.iv(iv),.ibank(ibank),.ib(ib),.ov(ro),.oy(ry),.oflt(rf));
 ot_s81c_attn_hcore dut(.clk(clk),.rst_n(rst_n),.gid(gid),.ld_v(dv),.ld_mode(dm),.ld_bank(db),.ld_grp(dg),.ld_w(dw[511:0]),.ld_wp(wp),.ld_w2v(d2),.iv(iv),.ibank(ibank),.ib(ib),.ov(d_o),.oy(dy),.oflt(df));
 reg[31:0]xs;integer cyc=0,err=0,nov=0,nz=0,phase,blk,invalid_diffs=0;
 function automatic[31:0]rnd(input integer dummy);reg[31:0]x;begin x=xs;x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);xs=x;rnd=x;end endfunction
 initial begin
  void'($value$plusargs("head=%d",gid_i));void'($value$plusargs("seed=%d",seed));void'($value$plusargs("mut=%d",mut));void'($value$plusargs("cycles=%d",ncyc));
  xs=32'h9e3779b9^(seed*32'h85ebca6b);re=0;rr=0;
 end
 always@(posedge clk)begin
  cyc<=cyc+1;
  if(cyc==3)rst_n<=1;
  // Production H8 block schedule: eight Qhead loads, QK beats, then
  // four paired Ploads at stride2; firstPVissue overlaps the last Pload.
  phase=(cyc>=60)?(cyc-60)%160:-1;blk=(cyc>=60)?(cyc-60)/160:0;
  if(cyc==941)rst_n<=0;if(cyc==951)rst_n<=1;
  ld_v<=((phase>=0&&phase<8)||(phase>=80&&phase<=86&&phase%2==0));
  ld_mode<=phase>=80&&phase<=86;
  ld_w2v<=1;
  ld_bank<=3'(blk%5);ld_grp<=8'(phase>=80?phase-80:phase);
  if(mut==2&&phase==81)begin ld_v<=1;ld_mode<=0;ld_grp<=gid;end
  for(integer i=0;i<32;i++)ld_w[32*i+:32]<=rnd(0);
  iv<=((phase>=16&&phase<=23)||(phase>=86&&phase<=93))&&blk!=5;
  ibank<=3'(blk%5);
  for(integer i=0;i<18;i++)ib[32*i+:32]<=rnd(0);
  if(rst_n&&cyc>8)begin
   if(ro!==d_o||(ro&&(ry!==dy||rf!==df)))begin err++;if(err<=5)$display("H8_RT2 mismatch cyc%0d ov%b/%b y%08x/%08x f%b/%b",cyc,ro,d_o,ry,dy,rf,df);end
   if(!ro&&(ry!==dy||rf!==df))invalid_diffs++;
   if(ro)begin nov++;if(ry!=0)nz++;end
  end
  if(cyc==ncyc)begin
   $display("H8_RT2 mut=%0d head=%0d seed=%0d mismatches=%0d ov=%0d nonzero=%0d invalid_data_diffs=%0d source_fault=%0d",mut,gid_i,seed,err,nov,nz,invalid_diffs,af);
   if(err==0&&nov>1000&&nz>100&&!af)$display("H8_RT2 PASS");else $display("H8_RT2 FAIL");$finish;
  end
 end
endmodule
