`timescale 1ns/1ps
module tb_head_mu_nr;
 reg ck=0;always #5 ck=~ck;reg rn=0,wv=0;reg[1103:0]wd=0;reg[10:0]rc=0;
 wire rv,nv,mv,f,nf,mf;wire[1103:0]rd,nd,md;
 dsdv_mu_land #(.NB(80),.NS(1),.SRAM(1),.W(1104))gold(.clk(ck),.rst_n(rn),.wv(wv),.wd(wd),.rc(rc),.rv(rv),.rd(rd),.fault(f));
 dsdv_mu_land_head_nr #(.NB(80),.NS(1),.SRAM(1),.W(1104))nr(.clk(ck),.rst_n(rn),.wv(wv),.wd(wd),.rc(rc),.rv(nv),.rd(nd),.fault(nf));
 dsdv_mu_land_head_nr_mut #(.NB(80),.NS(1),.SRAM(1),.W(1104))mut(.clk(ck),.rst_n(rn),.wv(wv),.wd(wd),.rc(rc),.rv(mv),.rd(md),.fault(mf));
 integer edge_n=0,checks=0,beats=0,mutants=0,j;
 always @(posedge ck)begin #1;edge_n=edge_n+1;
  if(edge_n>20)begin
   if({rv,f}!=={nv,nf})$fatal(1,"NR MU control/cycle mismatch");
   if(rv)begin
    if(rd!==nd)$fatal(1,"NR MU replay mismatch beat%0d",beats);
    if(md!==nd)mutants=mutants+1;beats=beats+1;
   end
   checks=checks+1;
  end
 end
 initial begin
  repeat(5)@(negedge ck);rn=1;repeat(25)@(negedge ck);
  for(integer pos=0;pos<3;pos=pos+1)begin
   for(integer b=0;b<80;b=b+1)begin
    for(j=0;j<35;j=j+1)wd=(wd<<32)|1104'($urandom);
    wd[1047+:10]=10'(513+pos);wd[1057+:21]=21'(pos);wv=1;@(negedge ck);
   end
   wv=0;repeat(10)@(negedge ck);rc={10'(513+pos),1'b1};@(negedge ck);rc=0;
   wait(rv);wait(!rv);repeat(12)@(negedge ck);
   if(f||nf)$fatal(1,"fault on valid native MU schedule");
  end
  if(beats!=240||mutants==0)$fatal(1,"missing replay/mutant beats%0d",beats);
  $display("HEAD_MU_NR PASS messages=3 replay_beats=%0d edge_checks=%0d wrong_address_mutant=%0d added_cycles=0",beats,checks,mutants);$finish;
 end
endmodule
