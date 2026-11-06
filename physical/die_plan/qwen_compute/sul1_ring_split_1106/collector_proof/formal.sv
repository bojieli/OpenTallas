module proof(input clk,rst,input [7:0] r0,f0,r1,f1);
wire a0,b0,c0,d0;g0 old0(clk,rst,r0,f0,a0,b0);t0 new0(clk,rst,r0,f0,c0,d0);always @* assert ({a0,b0}=={c0,d0});
wire a1,b1,c1,d1;g1 old1(clk,rst,r1,f1,a1,b1);t1 new1(clk,rst,r1,f1,c1,d1);always @* assert ({a1,b1}=={c1,d1});
endmodule
