`timescale 1ns/1ps
module tb_svc8_mapped;
 reg clk=0; always #1 clk=~clk;
 reg rst_n=0,ld_v=0,ld_mode=0,ld_w2v=0,iv=0;
 reg[7:0]gid=1,ld_grp=0;
 reg[2:0]ld_bank=0,ibank=0;
 reg[1023:0]ld_w=0;
 reg[255:0]ld_wp=0;
 reg[575:0]ib=0;
 wire vo,vn;wire[127:0]yo,yn;wire[3:0]fo,fn;
 ot_s81svc8_hgrp_s81 gold(.clk(clk),.rst_n(rst_n),.gid(gid),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_wp(ld_wp),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(vo),.oy(yo),.oflt(fo));
 ot_s81svc8_hgrp_s81_bounded cand(.clk(clk),.rst_n(rst_n),.gid(gid),.ld_v(ld_v),.ld_mode(ld_mode),.ld_bank(ld_bank),.ld_grp(ld_grp),.ld_w(ld_w),.ld_wp(ld_wp),.ld_w2v(ld_w2v),.iv(iv),.ibank(ibank),.ib(ib),.ov(vn),.oy(yn),.oflt(fn));
 integer cycle=0,seed=1,j,valids=0,first_valid=-1,post_reset_valids=0,checks=0;
 initial begin
  if($value$plusargs("seed=%d",seed));j=$urandom(seed);
  $display("SVC8_MAPPED_BEGIN seed=%0d reset=4 release_warm=8 initial_compare_from=1 independent_random_primitive_init=runtime_rand_reset2",seed);
 end
 always @(negedge clk) begin
  if(cycle==4)rst_n=1;
  if(cycle==180)rst_n=0;
  if(cycle==184)rst_n=1;
  ld_v=0;iv=0;
  for(j=0;j<64;j=j+1)ld_w[j*16+:16]={$urandom_range(0,1),8'(120+$urandom_range(0,16)),7'($urandom)};
  for(j=0;j<16;j=j+1)ld_wp[j*16+:16]={$urandom_range(0,1),8'(120+$urandom_range(0,16)),7'($urandom)};
  for(j=0;j<32;j=j+1)ib[j*18+:18]={2'b00,8'(127+$urandom_range(0,4)-2),8'($urandom)};
  ibank=$urandom_range(0,4);
  if(cycle>=12 &&cycle<32)begin
   ld_v=1;ld_mode=0;ld_w2v=0;ld_bank=(cycle-12)/4;ld_grp=gid*4+(cycle-12)%4;
  end
  if((cycle>=34&&cycle<178)||(cycle>=192))begin
   iv=$urandom_range(0,3)!=0;
   ld_v=$urandom_range(0,2)==0;ld_mode=$urandom_range(0,1);ld_w2v=$urandom_range(0,1);
   ld_bank=$urandom_range(0,4);ld_grp=$urandom_range(0,19);
  end
 end
 always @(posedge clk)begin
  cycle=cycle+1;
  #0.1;
  if(cycle>=1)begin
   if(cycle==2 && $test$plusargs("coupon_early_observer"))$fatal(1,"SVC8_EARLY_OBSERVER_CAUSAL");
   checks=checks+1;
   // No in-flight reset exclusion: once initial landing settles, validity is
   // checked on EVERY edge; data/fault checked on every valid edge.
   if(vo!==vn || ((vo||vn)&&({yo,fo}!=={yn,fn})))begin
    $display("SVC8_MAPPED_MISMATCH cycle=%0d rst=%b ov=%b/%b oy=%h/%h fault=%h/%h seed=%0d",cycle,rst_n,vo,vn,yo,yn,fo,fn,seed);
    $fatal(1,"SVC8_MAPPED_FAIL");
   end
   if(vo)begin
    valids=valids+1;if(first_valid<0)first_valid=cycle;
    if(cycle>=192)post_reset_valids=post_reset_valids+1;
   end
  end
  if(cycle==400)begin
   if(valids<20||post_reset_valids<20)$fatal(1,"SVC8_MAPPED_VACUOUS");
   $display("SVC8_MAPPED_PASS seed=%0d cycles=%0d checks=%0d valid=%0d first_valid=%0d post_reset_valid=%0d",seed,cycle,checks,valids,first_valid,post_reset_valids);
   $finish;
  end
 end
endmodule
