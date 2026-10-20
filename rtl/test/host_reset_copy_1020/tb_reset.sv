`timescale 1ns/1ps
module tb;
 reg clk=0,rst_n=1,d=0;always #0.5 clk=~clk;
 wire equal;wire q0,q1;
 common_reset u(.clk(clk),.rst_n(rst_n),.d(d),.equal(equal),.q0(q0),.q1(q1));
 int checks=0;
 initial begin
  // Independent initial states are an intentional verification deposit, never a design initialization assumption.
  u.q0=0;u.q1=1;
  #0.031;if(equal!==0)$fatal(1,"FAIL independent states disappeared before reset");
  for(int k=0;k<100;k++)begin
   #0.103;rst_n=0;
   #0.001;if(q0!==0||q1!==0||!equal)$fatal(1,"FAIL offphase assert k=%0d",k);
   #0.137;rst_n=1;
   @(posedge clk);#0.001;if(!equal)$fatal(1,"FAIL first valid k=%0d",k);checks++;
   repeat(5)begin @(negedge clk);d=~d;@(posedge clk);#0.001;if(!equal)$fatal(1,"FAIL induction");checks++;end
  end
  $display("PASS RESET_COPY offphase100 firstvalid100 independent_init checks=%0d",checks);$finish;
 end
endmodule
