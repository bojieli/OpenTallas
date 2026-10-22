module top(input wire clk,rst_n,input wire[31:0]x_flat,x_bound,output wire[31:0]y_flat,y_bound);
leaf #(.N(32)) u_flat(.clk(clk),.rst_n(rst_n),.x(x_flat),.y(y_flat));
leaf_c u_bound(.clk(clk),.rst_n(rst_n),.x(x_bound),.y(y_bound));
endmodule
