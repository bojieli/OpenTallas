`timescale 1ns/1ps
module example__ot_pr_core(input wire ck,rst_n,output wire q);assign q=rst_n;endmodule
module tb_reset;
 reg ck=0;always #1 ck=~ck;
 reg rst_n=0;wire q;example dut(ck,rst_n,q);
 reg r0=0,r1=0;integer checks=0;
 always @(posedge ck)begin
  r1=r0;r0=rst_n;#0.01;
  if($time>5)begin
   if(q!==r1)$fatal(1,"RESET_EDGE_MISMATCH");
   for(integer j=0;j<11;j++)if(dut.rst_n__ot_rl0c[j]!==r0)$fatal(1,"FIRST_COPY");
   for(integer j=0;j<287;j++)if(dut.rst_n__ot_rlc[j]!==r1)$fatal(1,"LAST_COPY");
   checks++;
  end
 end
 initial begin
  for(integer k=0;k<2000;k++)begin
   #0.137;rst_n=~rst_n;
   #(0.071+0.037*(k%71));
  end
  #10;$display("RESET_PHASE_PASS checks=%0d two_edges=1",checks);$finish;
 end
endmodule
