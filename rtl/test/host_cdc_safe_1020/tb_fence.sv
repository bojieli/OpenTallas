`timescale 1ns/1ps
module tb;
 reg ck=0,ch=0,rst=0;always #0.5 ck=~ck;always #0.71 ch=~ch;
 reg[7:0]ack=0;reg iv=0,oc=0;reg[63:0]id=0;
 wire[1:0]ic,ov,fault;wire[63:0]d[0:1];wire[31:0]land[0:1];
 qkd_hr_visibility_fence_cdc a(.rst_n(rst),.ck(ck),.clk_h(ch),.ack_n(ack),.in_v(iv),.in_d(id),.in_cr(ic[0]),.out_v(ov[0]),.out_d(d[0]),.out_cr(oc),.fault(fault[0]),.landed_debug(land[0]));
 qkd_hr_visibility_fence_sram b(.rst_n(rst),.ck(ck),.clk_h(ch),.ack_n(ack),.in_v(iv),.in_d(id),.in_cr(ic[1]),.out_v(ov[1]),.out_d(d[1]),.out_cr(oc),.fault(fault[1]),.landed_debug(land[1]));
 int seed=42,ignored,cycle=0,credits=4,owed=0,sent=0,got=0,done_sent=0,blocked=0;
 initial begin ignored=$urandom(seed);#9.13;rst=1;#25000;$display("FAIL timeout");$finish(1);end
 always @(negedge ck)ack<=rst?8'($urandom_range(0,2)):0;
 always @(negedge ch)begin
  cycle++;
  if(cycle==5000||cycle==10000)rst=0;
  if(cycle==5006||cycle==10006)rst=1;
  if(!rst||cycle<25)begin iv=0;oc=0;credits=4;owed=0;end else begin
   credits+=ic[0];owed+=ov[0];
   if(a.g_on.count!=0 && a.g_on.is_done && a.g_on.landed<a.g_on.head[31:0])blocked++;
   iv=(credits>0)&&($urandom_range(0,3)!=0);oc=(owed>0)&&($urandom_range(0,3)!=0);
   if(oc)owed--;
   if(iv)begin
    credits--;sent++;
    id={$urandom,$urandom};
    if($urandom_range(0,3)==0)begin id[63:56]=1;id[31:0]=land[0]+32'($urandom_range(0,30));done_sent++;end
    else id[63:56]=2;
   end
  end
  if(cycle==15000)begin
   if(sent<1000||got<1000||done_sent<100||blocked<100)$fatal(1,"FAIL coverage");
   $display("PASS HOST_FENCE cycles=%0d sent=%0d got=%0d done=%0d blocked=%0d",cycle,sent,got,done_sent,blocked);$finish;
  end
 end
 always @(posedge ch)begin #0.002;
  if(ic[0]!==ic[1]||ov[0]!==ov[1]||fault[0]!==fault[1]||land[0]!==land[1])$fatal(1,"FAIL control t=%0t",$time);
  if(ov[0]&&d[0]!==d[1])$fatal(1,"FAIL payload t=%0t old=%h new=%h",$time,d[0],d[1]);
  if(ov[0])got++;
 end
endmodule
