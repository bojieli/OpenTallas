`timescale 1ps/1ps
module tb;
 reg clk=0;always begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,ld_v=0,ld_mode=0,ld_w2v=0,iv=0;
 reg[7:0]gid=3,ld_grp=0;reg[2:0]ld_bank=0,ibank=0;
 reg[511:0]ld_w=0;reg[63:0]ld_wp=0;reg[575:0]ib=0;
 wire rov,dov,rf,df;wire[31:0]ry,dy;
 integer cyc=0,nov=0,nz=0,mism=0;reg mutant=0;
 wire div=iv && !(mutant && cyc>1000);
 ot_s81c_attn_hcore #(.WPRE(2),.BZ0(1),.WSEG(0)) refcore(.clk(clk),.rst_n(rst_n),.gid(gid),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_wp(ld_wp),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(rov),.oy(ry),.oflt(rf));
 ot_s81c_attn_hcore_5 dut(.clk(clk),.rst_n(rst_n),.gid(gid),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_wp(ld_wp),.ld_w2v(ld_w2v),.iv(div),.ibank(ibank),.ib(ib),.ov(dov),.oy(dy),.oflt(df));
 reg[31:0]xs=32'h9e3779b9;
 function[31:0]rnd(input integer dummy);reg[31:0]x;begin x=xs;x=x^(x<<13);x=x^(x>>17);x=x^(x<<5);xs=x;rnd=x;end endfunction
 initial mutant=$test$plusargs("mutant");
 always@(negedge clk)begin
  cyc=cyc+1;rst_n=(cyc>8 && !(cyc>=10000 && cyc<10008));
  ld_v=(cyc<400)?(rnd(0)%8!=0):(rnd(0)%4==0);
  ld_mode=rnd(0)%3==0;ld_w2v=rnd(0)%2;ld_bank=3'(rnd(0)%6);
  ld_grp=(rnd(0)%16==0)?8'(rnd(0)):8'(rnd(0)%17);
  for(integer i=0;i<16;i++)ld_w[32*i+:32]=rnd(0);
  for(integer i=0;i<2;i++)ld_wp[32*i+:32]=rnd(0);
  iv=(cyc<300)?0:(rnd(0)%4!=0);ibank=3'(rnd(0)%5);
  for(integer i=0;i<18;i++)ib[32*i+:32]=rnd(0);
 end
 always@(posedge clk)begin #2;
  if(cyc>16)begin
   if(rov!==dov || ry!==dy || rf!==df)begin mism++;if(mism<5)$display("MISMATCH cyc=%0d ov=%b/%b y=%h/%h f=%b/%b",cyc,rov,dov,ry,dy,rf,df);end
   if(rov)begin nov++;if(ry!=0)nz++;end
  end
  if(cyc==20000)begin
   $display("NATIVE_HCORE_WRAPPER mutant=%0d mismatches=%0d ov=%0d nonzero=%0d",mutant,mism,nov,nz);
   if(mutant ? (mism==0) : (mism!=0 || nov<1000 || nz<100))$fatal(1,"NATIVE_HCORE_WRAPPER_FAIL");
   $display("PASS_NATIVE_HCORE_WRAPPER");$finish;
  end
 end
endmodule
