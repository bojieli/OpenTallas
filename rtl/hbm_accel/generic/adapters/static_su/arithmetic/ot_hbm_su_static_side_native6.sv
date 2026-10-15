// Physical-boundary adapter: six scalar clock pins, unchanged SIDE logic/latency.
module ot_hbm_su_static_side_native6(input ck0,ck1,ck2,ck3,ck4,ck5,rst_n,v,input [2:0] fn,fn_out,input [31:0] x,output [31:0] y,output fault);
ot_hbm_su_static_side u_side(.clk({ck5,ck4,ck3,ck2,ck1,ck0}),.rst_n(rst_n),.v(v),.fn(fn),.fn_out(fn_out),.x(x),.y(y),.fault(fault));
endmodule
