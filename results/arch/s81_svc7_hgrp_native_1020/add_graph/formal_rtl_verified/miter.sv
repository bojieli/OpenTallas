module svc7_graph_miter(input clk,rst_n,v,input [31:0] a,b,output bad);
  wire [31:0] x,y;
  wire [1:0] xe,ye;
  wire xv,yv;
  ot_s81svc7_add_graph_input original(.clk(clk),.rst_n(rst_n),.valid_in(v),
     .a(a),.b(b),.y(x),.err(xe),.valid_out(xv));
  ot_s81svc7_add_native candidate(.clk(clk),.rst_n(rst_n),.valid_in(v),
     .a(a),.b(b),.y(y),.err(ye),.valid_out(yv));
  // No in-flight reset mask: compare validity every edge and data on validity.
  assign bad=(xv!=yv) | ((xv|yv) & ({xe,x}!={ye,y}));
endmodule
