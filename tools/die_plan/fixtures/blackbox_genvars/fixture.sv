module hard(input clk,input [3:0] d,output [3:0] q);
 genvar gf;
 generate for(gf=0;gf<4;gf=gf+1)begin:g
 reg v;always @(posedge clk)v<=d[gf];assign q[gf]=v;
 end endgenerate
endmodule
module top(input clk,input[3:0] d,output[3:0]q);
hard u(.clk(clk),.d(d),.q(q));
endmodule
