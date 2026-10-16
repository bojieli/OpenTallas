`timescale 1ns/1ps
module tb;
 reg ck=0,rst_n=0; reg[41:0]a=0;wire[41:0]b0,b1;
 qfd_static_command_fork42 dut(.*);
 always #5 ck=~ck;
 integer k,checked=0;reg[41:0]expected;
 initial begin
  #1;rst_n=1;#1;rst_n=0;
  repeat(3)@(negedge ck);
  if(b0!==0||b1!==0)$fatal(1,"cold reset");
  rst_n=1;
  // One reset synchronizer edge, then each source event arrives on one edge.
  @(negedge ck);
  for(k=0;k<2048;k=k+1)begin
   a={$urandom,$urandom};expected=a;
   @(posedge ck);#1;
   if(b0!==expected||b1!==expected)$fatal(1,"fork exact edge k=%0d got%h/%h expected%h",k,b0,b1,expected);
   checked=checked+1;@(negedge ck);
  end
  rst_n=0;#1;if(b0!==0||b1!==0)$fatal(1,"asynchronous clear");
  $display("PASS COMMAND_FORK checked=%0d fixed_latency=1 branches=2",checked);$finish;
 end
endmodule
