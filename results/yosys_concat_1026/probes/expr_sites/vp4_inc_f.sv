module vp4_inc(input [31:0] x, output [31:0] y);
 
 assign y = {x[31:24]+{7'd0,&x[23:0]},x[23:16]+{7'd0,&x[15:0]},x[15:8]+{7'd0,&x[7:0]},x[7:0]+8'd1};
endmodule
