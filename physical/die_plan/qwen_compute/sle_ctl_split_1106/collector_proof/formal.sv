module proof(input clk,rst,input [23:0] r0, f0,
input [20:0] r1, f1,
input [22:0] r2, f2,
input [25:0] r3, f3);
wire a0,b0,c0,d0;
g0 g_0(clk,rst,r0,f0,a0,b0); t0 t_0(clk,rst,r0,f0,c0,d0);
always @* assert({a0,b0} == {c0,d0});
wire a1,b1,c1,d1;
g1 g_1(clk,rst,r1,f1,a1,b1); t1 t_1(clk,rst,r1,f1,c1,d1);
always @* assert({a1,b1} == {c1,d1});
wire a2,b2,c2,d2;
g2 g_2(clk,rst,r2,f2,a2,b2); t2 t_2(clk,rst,r2,f2,c2,d2);
always @* assert({a2,b2} == {c2,d2});
wire a3,b3,c3,d3;
g3 g_3(clk,rst,r3,f3,a3,b3); t3 t_3(clk,rst,r3,f3,c3,d3);
always @* assert({a3,b3} == {c3,d3});
endmodule
