`timescale 1ns/1ps
module tb_skid_cx #(parameter integer MUT=0);
 reg clk=0;always #0.5 clk=~clk;
 reg rst_n=0,in_v=0,out_ready=0;reg[4113:0]in_d=0;
 wire ar,br,av,bv;wire[4113:0]ad,bd;
 ot_hfd_mtp_skid #(.W(4114)) original(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_ready(ar),.in_d(in_d),.out_v(av),.out_ready(out_ready),.out_d(ad));
 ot_hfd_mtp_skid_banked_cx #(.W(4114),.BANKED(1),.MUT_SPARE(MUT)) candidate(.clk(clk),.rst_n(rst_n),.in_v(in_v),.in_ready(br),.in_d(in_d),.out_v(bv),.out_ready(out_ready),.out_d(bd));
 integer n,k;integer empty_no_input=0,stalled=0,pop_push=0,promotion=0;
 always@(posedge clk)if(rst_n)begin
  if(ar!==br||av!==bv||(av&&ad!==bd))$fatal(1,"SKID_CX FAIL n=%0d",n);
  if(!original.s_v&&!in_v)empty_no_input=empty_no_input+1;
  if(av&&!out_ready)stalled=stalled+1;
  if(av&&out_ready&&in_v&&ar)pop_push=pop_push+1;
  if(original.s_v&&(!av||out_ready))promotion=promotion+1;
 end
 initial begin
  repeat(4)@(negedge clk);rst_n=1;
  for(n=0;n<1200;n=n+1)begin
   @(negedge clk);
   in_v=(n<12)?1:((n%7)!=0);
   out_ready=(n<12)?0:((n%9)>=3);
   for(k=0;k<129;k=k+1)if(k<128)in_d[k*32+:32]=(n*7919+k*104729)^32'habadcafe;
   in_d[4096+:18]=18'(n);
  end
  @(negedge clk);in_v=0;out_ready=1;repeat(8)@(negedge clk);
  if(empty_no_input==0||stalled==0||pop_push==0||promotion==0)$fatal(1,"SKID_CX missing mechanism coverage");
  $display("SKID_CX PASS empty_no_input=%0d stalled=%0d pop_push=%0d promotion=%0d",empty_no_input,stalled,pop_push,promotion);$finish;
 end
endmodule
