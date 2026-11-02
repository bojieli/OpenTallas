`timescale 1ps/1ps
module tb;
 reg clk=0,rst_n=0;always begin #416 clk=1;#417 clk=0;end
 wire[63:0]q;parent u(.clk(clk),.rst_n(rst_n),.q(q));
 integer cycles=0;
 always@(posedge clk)begin cycles++;#1;if(cycles==2)rst_n=1;if(cycles==10)begin
  for(integer i=0;i<8;i++)if(q[8*i+:8]!=8*(3+i))$fatal(1,"COUNTER_MISMATCH got=%d",q[8*i+:8]);
  $display("PASS_HIERARCHY_TOOL_REPRODUCER cycles=%d q=%h",cycles,q);$finish;
 end end
endmodule
