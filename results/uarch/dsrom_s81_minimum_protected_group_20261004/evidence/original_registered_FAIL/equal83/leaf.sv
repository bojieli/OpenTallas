module leaf(input clk,input [165:0] din,output reg [0:0] q);
reg [165:0] d;

always @(posedge clk) begin d<=din;q<=(d[82:0]==d[165:83]);end
endmodule
