`timescale 1ps/1fs
module tb_write_observer_wl #(parameter integer WL=7,MUT=0);
 reg clk=0,rst_n=0;always #416.5 clk=~clk;
 reg[327:0]po=0;reg sc=0,expected=0;reg[346:0]ctx=0;
 wire cv,f;wire[60:0]ci;wire[28:0]ca;
 qkd_static_kv_write_observer #(.WL(WL)) dut(clk,rst_n,po,sc,expected,ctx,cv,ci,ca,f);
 integer n=0,commits=0;
 // Independent known ECC for all-zero payload is all zero; mutation corrupts physical write data.
 always @(negedge clk)if(rst_n)begin
   if(f)$fatal(1,"OBSERVER fault MUT%0d",MUT);
   if(cv)begin if(ci!=61'h123||ca!=29'h400)$fatal(1,"OBSERVER identity");commits++;end
 end
 initial begin
  repeat(5)@(negedge clk);rst_n=1;
  // ACT bank0,row1, matching descriptor {row,bank,col}.
  po[0]=1;po[3:1]=1;po[27:9]=1;
  @(negedge clk);po=0;
  repeat(3)@(negedge clk);
  po[28]=1;po[29]=1;sc=1;expected=1;ctx={1'b1,61'h123,29'h400,256'b0};
  @(negedge clk);po=0;sc=0;expected=0;ctx=0;
  repeat(WL-1)@(negedge clk);
  if(MUT)po[40]=1;
  repeat(3)@(negedge clk);
  if(commits!=1)$fatal(1,"OBSERVER commits %0d",commits);
  $display("PASS observer WL%0d commits%0d",WL,commits);$finish;
 end
endmodule
