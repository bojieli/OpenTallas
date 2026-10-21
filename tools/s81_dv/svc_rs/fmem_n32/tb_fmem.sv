`timescale 1ns/1ps
module tb_fmem;
 reg clk=0;always #5 clk=~clk;
 reg we=0;reg[4:0]wa=0,ra=0;reg[2119:0]wd=0;
 wire[2119:0]rd[0:2],gold[0:2],rd0[0:2],gold0[0:2];
 integer checks=0,errors=0,collisions=0,negative=0;
 for(genvar t=0;t<3;t=t+1)begin:g
  localparam integer W=(t==0)?2120:(t==1)?527:286;
  wire[W-1:0]a,b,c,d;
  dsdv_svc_fmem #(.W(W),.BYP(1))dut(.clk(clk),.we(we),.wa(wa),.wd(wd[W-1:0]),.ra(ra),.rd(a),.we_reps({((W+255)/256){we}}));
  dsdv_svc_fmem_ref #(.W(W),.BYP(1))refdut(.clk(clk),.we(we),.wa(wa),.wd(wd[W-1:0]),.ra(ra),.rd(b));
  dsdv_svc_fmem #(.W(W),.BYP(0))dut0(.clk(clk),.we(we),.wa(wa),.wd(wd[W-1:0]),.ra(ra),.rd(c),.we_reps({((W+255)/256){we}}));
  dsdv_svc_fmem_ref #(.W(W),.BYP(0))ref0(.clk(clk),.we(we),.wa(wa),.wd(wd[W-1:0]),.ra(ra),.rd(d));
  assign rd[t]=2120'(a);assign gold[t]=2120'(b);assign rd0[t]=2120'(c);assign gold0[t]=2120'(d);
 end
 initial begin
  for(integer c=0;c<2200;c=c+1)begin
   @(negedge clk);we=c<32||(c%4!=1);wa=5'(c%32);ra=c%3==0?wa:5'((c*13+7)%32);
   for(integer j=0;j<67;j=j+1)wd=(wd<<32)^32'(c*79919+j*1237);
   @(posedge clk);#1;
   if(c>=40)begin
    checks=checks+1;if(we&&wa==ra)collisions=collisions+1;
    for(integer t=0;t<3;t=t+1)begin
     if(rd[t]!==gold[t]||rd0[t]!==gold0[t])begin errors=errors+1;if(errors<5)$display("FMEM_MISMATCH c=%0d widthindex=%0d",c,t);end
     if(rd0[t]!==gold[t])negative=negative+1;
    end
   end
  end
  $display("FMEM_RESULT checks=%0d collisions=%0d errors=%0d no_bypass_mismatches=%0d",checks,collisions,errors,negative);
  if(checks<2000||collisions<500||errors!=0||negative<1500)$fatal(1,"fmem qualification");$finish;
 end
endmodule
