module forest_top #(parameter integer W=1073)(input wire clk,rst_n,input wire[W-1:0] i,output wire[W-1:0] o);
wire[W-1:0] hop;
forest_child #(.W(W)) u0(.clk(clk),.rst_n(rst_n),.i(i),.o(hop));
forest_child #(.W(W)) u1(.clk(clk),.rst_n(rst_n),.i(hop),.o(o));endmodule
