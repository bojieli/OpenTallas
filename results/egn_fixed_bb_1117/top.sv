module top(input clk,rst_n,i_v,input [31:0] i_x,eps,output o_v,o_f,output [31:0]o_r);
ot_s81sl_egn #(.LA(4),.LM(5)) u(.clk(clk),.rst_n(rst_n),.i_v(i_v),.i_x(i_x),.eps(eps),.o_v(o_v),.o_f(o_f),.o_r(o_r));
endmodule
