module tb(input clk,input [106:0] d,input [4:0] rn,output bad);
wire [508:0] a,b;
sc_pin_gold g(clk,d,rn,a);sc_pin_gate h(clk,d,rn,b);
reg ready=0;always @(posedge clk) ready<=1;
assign bad=ready && (|(a^b));
endmodule
