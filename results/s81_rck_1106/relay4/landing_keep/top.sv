module top(input clk,rst,input[31:0] a,input[63:0] b,output[31:0] x,output[63:0] y);
wire[127:0] ab;wire[11:0]ae;wire[3:0]av;
wire[255:0] bb;wire[11:0]be;wire[3:0]bv;
ot_pl_land_w #(.W(32)) wa(.ck(clk),.rsi(rst),.i(a),.bank(ab),.epo(ae),.vld(av));
ot_pl_land_w #(.W(64)) wb(.ck(clk),.rsi(rst),.i(b),.bank(bb),.epo(be),.vld(bv));
ot_pl_land_r #(.W(32)) ra(.ck(clk),.rsi(rst),.bank(ab),.epo(ae),.vld(av),.o(x));
ot_pl_land_r #(.W(64)) rb(.ck(clk),.rsi(rst),.bank(bb),.epo(be),.vld(bv),.o(y));
endmodule
