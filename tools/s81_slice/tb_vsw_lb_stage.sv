`timescale 1ns/1ps
module tb;
reg clk=0,rst_n=0;always #0.5 clk=~clk;
reg i_v=0;reg[255:0]i_d=0;reg[31:0]i_w=0,i_lim=0;
wire v0,f0,v1,f1;wire[63:0]d0,d1;
ot_s81sl_vsw #(.LB_STAGE(0)) refm(clk,rst_n,i_v,i_d,i_w,i_lim,v0,d0,f0);
ot_s81sl_vsw #(.LB_STAGE(1)) cand(clk,rst_n,i_v,i_d,i_w,i_lim,v1,d1,f1);
integer cyc=0,checks=0,nov=0,seed=1,gap=0,k;
function[31:0]rfp(input integer z);reg[31:0]r;begin r=$random(seed);r[30:23]=112+($random(seed)&31);rfp=r;end endfunction
always@(posedge clk)begin
 cyc<=cyc+1;
 if(cyc>10)begin checks=checks+1;if({v0,f0,d0}!=={v1,f1,d1})$fatal(1,"DIFF cyc%0d ref %b %b %h candidate %b %b %h",cyc,v0,f0,d0,v1,f1,d1);end
 if(v0)nov=nov+1;
end
initial begin
 if($value$plusargs("SEED=%d",seed))begin end
 repeat(6)@(negedge clk);rst_n=1;
 for(k=0;k<40000;k=k+1)begin
  @(negedge clk);
  if(k==20000)begin rst_n=0;repeat(5)@(negedge clk);rst_n=1;end
  if(gap==0)begin i_v=1;i_d={rfp(0),rfp(0),rfp(0),rfp(0),rfp(0),rfp(0),rfp(0),rfp(0)};i_w=rfp(0);i_lim=rfp(0);gap=(($random(seed)&15)==0)?1+($random(seed)&1):4+($random(seed)&3);end
  else begin i_v=0;i_d={8{$random(seed)}};i_w=$random(seed);i_lim=$random(seed);end
  gap=gap-1;
 end
 repeat(300)@(negedge clk);
 if(nov<100)$fatal(1,"no valid output");
 $display("PASS VSW_LB samecycle ALL outputs %0d checks %0d valid",checks,nov);$finish;
end
endmodule
