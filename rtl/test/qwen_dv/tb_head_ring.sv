`timescale 1ns/1ps
module tb_head_ring;
 reg clk=0; always #5 clk=~clk;
 reg rst_n=0; reg[139:0] d;
 wire[139:0] q11;wire[132:0] q5;wire[34:0] q4;wire[125:0] q10;
 qfd_dv_head_sram_delay #(.W(140),.D(11)) a(clk,rst_n,d,q11);
 qfd_dv_head_sram_delay #(.W(133),.D(5)) b(clk,rst_n,d[132:0],q5);
 qfd_dv_head_sram_delay #(.W(35),.D(4)) c(clk,rst_n,d[34:0],q4);
 qfd_dv_head_sram_delay #(.W(126),.D(10)) e(clk,rst_n,d[125:0],q10);
 reg[139:0] hist[0:10]; integer n,k,age=0,checks=0;
 initial begin
  d=0;
  for(n=0;n<2200;n=n+1) begin
   @(negedge clk);
   rst_n= !((n<3)||(n>=508&&n<512)||(n>=1097&&n<1101));
   d={$random,$random,$random,$random,$random};
   @(posedge clk);
   for(k=10;k>0;k=k-1) hist[k]=hist[k-1];
   hist[0]=d;
   if(!rst_n) age=0; else age=age+1;
   #1;
   if(age>40) begin
    if(q11!==hist[10]||q5!==hist[4][132:0]||q4!==hist[3][34:0]||q10!==hist[9][125:0])
     $fatal(1,"HEAD_RING_AGE_FAIL n=%0d",n);
    checks=checks+4;
   end
  end
  $display("HEAD_RING_PASS checks=%0d resets=3 wraps>60",checks); $finish;
 end
endmodule
