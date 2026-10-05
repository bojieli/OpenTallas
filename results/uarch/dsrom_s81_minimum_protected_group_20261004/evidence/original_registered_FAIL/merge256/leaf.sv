module leaf(input clk,input [519:0] din,output reg [255:0] q);
reg [519:0] d;
function automatic [255:0] merge(input [519:0] x);
reg [255:0] z;integer k;begin
z=x[255:0];for(k=0;k<8;k=k+1)if(x[512+k])z[32*k+:32]=x[256+32*k+:32];merge=z;end endfunction
always @(posedge clk) begin d<=din;q<=merge(d);end
endmodule
