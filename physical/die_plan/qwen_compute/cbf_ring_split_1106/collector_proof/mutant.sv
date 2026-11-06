module proof_mut(input clk,rst,input [6:0] r,f);reg z=0;always @(posedge clk)z<=r[0];wire a,b,c,d;gold g(clk,rst,r,f,a,b);gate t(clk,rst,{r[6:1],z},f,c,d);always @* assert({a,b}=={c,d});endmodule
