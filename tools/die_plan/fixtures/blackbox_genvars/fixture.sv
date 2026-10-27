module hard(input clk,input [3:0] d,output [3:0] q);
 genvar gf;
 localparam integer ADD_LAT=7, ZW=4;
 generate for(gf=0;gf<4;gf=gf+1)begin:g
 reg v;always @(posedge clk)v<=d[gf];assign q[gf]=v;
 end endgenerate
endmodule
module top(input clk,input[3:0] d,output[3:0]q);
hard u(.clk(clk),.d(d),.q(q));
endmodule
