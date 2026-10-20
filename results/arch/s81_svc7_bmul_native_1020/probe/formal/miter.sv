module svc7_graph_miter(input clk,rst_n,pad,input [15:0] a,b,output bad);
 wire [31:0] x,y; wire xf,yf;
 ot_s81svc7_bmul_graph_input original(.clk(clk),.rst_n(rst_n),.pad(pad),.a(a),.b(b),.y(x),.flt(xf));
 ot_s81svc7_bmul_native candidate(.clk(clk),.rst_n(rst_n),.pad(pad),.a(a),.b(b),.y(y),.flt(yf));
 // No validity/reset mask. Compare every output after initial pipeline flush.
 assign bad=({xf,x}!={yf,y});
endmodule
