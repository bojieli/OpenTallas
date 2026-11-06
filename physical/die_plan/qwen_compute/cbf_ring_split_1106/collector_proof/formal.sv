module proof(input clk,rst,input [6:0] r,f); wire a,b,c,d;gold g(clk,rst,r,f,a,b);gate t(clk,rst,r,f,c,d);always @* assert({a,b}=={c,d});endmodule
