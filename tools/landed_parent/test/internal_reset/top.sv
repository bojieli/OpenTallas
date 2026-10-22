module lpt_top #(parameter integer W = 8) (input wire clk,input wire rst_n,input wire [1:0] xk,input wire [W-1:0] x,output wire [W-1:0] z, zf);
 wire reset_local; wire [W-1:0] y0,y1;
 lpt_rst ur (.clk(clk),.rst_n(rst_n),.rs(reset_local));
 lpt_leaf #(.W(W)) u0 (.clk(clk),.rst_n(reset_local),.a(x),.b(y1),.y(y0));
 lpt_leaf #(.W(W)) u1 (.clk(clk),.rst_n(reset_local),.a(y0),.b(x),.y(y1));
 lpt_fwd uf (.clk(xk[1]),.x(x),.y(zf));
 assign z=y1;
endmodule
