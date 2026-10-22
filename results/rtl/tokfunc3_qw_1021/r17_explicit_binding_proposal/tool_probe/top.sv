module top(input wire clk,rst_n,input wire[31:0]x,output wire[31:0]y);
leaf #(.N(32)) u_leaf(.clk(clk),.rst_n(rst_n),.x(x),.y(y));
endmodule
