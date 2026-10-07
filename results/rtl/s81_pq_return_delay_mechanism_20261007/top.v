module top(input clk,input a,input b,output qa,output qb);
wire n0,n1;
BUFx2_ASAP7_75t_R source0(.A(a),.Y(n0));
BUFx2_ASAP7_75t_R source1(.A(b),.Y(n1));
DFFHQNx1_ASAP7_75t_R q0(.CLK(clk),.D(n0),.QN(qa));
DFFHQNx1_ASAP7_75t_R q1(.CLK(clk),.D(n1),.QN(qb));
endmodule
