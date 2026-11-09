`timescale 1ns/1ps
// One native H8 head versus the same H8 behavioral head group. Actual CTLA
// sender and private timed reset are included. All32 dot-product lanes/order
// retained; only preselection of RT4 P columns differs. No physical claim.
module tb_s81c_hcore_h8;
 localparam H=8,TD=32,R=4;
 reg clk=0;always#0.5 clk=~clk;
 reg rst_n=0,ld_v=0,ld_mode=0,ld_w2v=0,iv=0;
 reg[2:0]ld_bank=0,ibank=0;reg[7:0]ld_grp=0;
 reg[1023:0]ld_w=0;reg[575:0]ib=0;
 wire lv,lm,l2;wire[2:0]lb;wire[7:0]lg;wire[1023:0]lw;
 ot_s81c_hcore_load_stage u_stage(.clk(clk),.rst_n(rst_n),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_w2v(ld_w2v),.out_v(lv),.out_mode(lm),.out_bank(lb),.out_grp(lg),.out_w(lw),.out_w2v(l2));
 integer gid_i=0,seed=1,mut=0,ncyc=8000;
 wire[7:0]gid=8'(gid_i);
 wire[127:0]wp;
 for(genvar w=0;w<2;w++)for(genvar j=0;j<4;j++)begin:pcols
  wire[7:0]h=(mut==1&&w==1)?8'((gid_i+1)%8):gid;
  assign wp[16*(4*w+j)+:16]=lw[w*512+16*(8*j+h)+:16];
 end
 reg re,rr;
 always@(posedge clk)begin re<=rst_n;rr<=re;end
 wire ro,d_o,rf,df;wire[31:0]ry,dy;
 ot_hdc_v41x_attn_hgrp_s #(.H(8),.HG(1),.TD(32),.NBANK(5),.BW(3),.PWORDS(2),.FPL(4),.FML(6),.F12(1),.PCOLP(0),.WPRE(2),.BZ0(1)) ref_h(
  .clk(clk),.rst_n(rr),.gid(gid),.ld_v(lv),.ld_mode(lm),.ld_bank(lb),.ld_grp(lg),.ld_w(lw),.ld_wp(128'd0),.ld_w2v(l2),.iv(iv),.ibank(ibank),.ib(ib),.ov(ro),.oy(ry),.oflt(rf));
 ot_s81c_attn_hcore_h8 dut(.clk(clk),.rst_n(rst_n),.gid(gid),.ld_v(lv),.ld_mode(lm),.ld_bank(lb),.ld_grp(lg),.ld_w(lw[511:0]),.ld_wp(wp),.ld_w2v(l2),.iv(iv),.ibank(ibank),.ib(ib),.ov(d_o),.oy(dy),.oflt(df));
 reg[31:0]xs;integer cyc=0,err=0,nov=0,nz=0;
 function automatic[31:0]rnd(input integer dummy);reg[31:0]x;begin x=xs;x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);xs=x;rnd=x;end endfunction
 initial begin
  void'($value$plusargs("head=%d",gid_i));void'($value$plusargs("seed=%d",seed));void'($value$plusargs("mut=%d",mut));void'($value$plusargs("cycles=%d",ncyc));
  xs=32'h9e3779b9^(seed*32'h85ebca6b);re=0;rr=0;
 end
 always@(posedge clk)begin
  cyc<=cyc+1;
  if(cyc==3)rst_n<=1;
  // Repeated boot exercises real reset entry/relay on an active pipeline.
  if(cyc==3000)rst_n<=0;if(cyc==3010)rst_n<=1;
  ld_v<=(cyc<400)?(rnd(0)%8!=0):(rnd(0)%4==0);
  ld_mode<=rnd(0)%3==0;ld_w2v<=rnd(0)%2;
  ld_bank<=3'(rnd(0)%6);ld_grp<=(rnd(0)%16==0)?8'(rnd(0)):8'(rnd(0)%17);
  for(integer i=0;i<32;i++)ld_w[32*i+:32]<=rnd(0);
  iv<=(cyc>=300)&&(rnd(0)%4!=0);ibank<=3'(rnd(0)%5);
  for(integer i=0;i<18;i++)ib[32*i+:32]<=rnd(0);
  if(rst_n&&cyc>8)begin
   if(ro!==d_o||ry!==dy||rf!==df)begin err++;if(err<=5)$display("H8_HEAD mismatch cyc%0d ov%b/%b y%08x/%08x f%b/%b",cyc,ro,d_o,ry,dy,rf,df);end
   if(ro)begin nov++;if(ry!=0)nz++;end
  end
  if(cyc==ncyc)begin
   $display("H8_HEAD mut=%0d head=%0d seed=%0d mismatches=%0d ov=%0d nonzero=%0d",mut,gid_i,seed,err,nov,nz);
   if(err==0&&nov>1000&&nz>100)$display("H8_HEAD PASS");else $display("H8_HEAD FAIL");$finish;
  end
 end
endmodule
