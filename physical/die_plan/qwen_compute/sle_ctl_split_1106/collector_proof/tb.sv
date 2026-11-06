module tb; reg clk=0,rst=0; always #5 clk=~clk; integer n=0,bad=0,j;
reg [23:0] r0=0,f0=0; wire a0,b0,c0,d0;
g0 g_0(clk,rst,r0,f0,a0,b0); t0 t_0(clk,rst,r0,f0,c0,d0);
reg [20:0] r1=0,f1=0; wire a1,b1,c1,d1;
g1 g_1(clk,rst,r1,f1,a1,b1); t1 t_1(clk,rst,r1,f1,c1,d1);
reg [22:0] r2=0,f2=0; wire a2,b2,c2,d2;
g2 g_2(clk,rst,r2,f2,a2,b2); t2 t_2(clk,rst,r2,f2,c2,d2);
reg [25:0] r3=0,f3=0; wire a3,b3,c3,d3;
g3 g_3(clk,rst,r3,f3,a3,b3); t3 t_3(clk,rst,r3,f3,c3,d3);
always @(negedge clk) begin n=n+1; rst=(n>12);
r0 = '1; f0 = '0; if(n%7==0)r0[n%24]=0; if(n%5==0)f0[n%24]=1;
r1 = '1; f1 = '0; if(n%7==0)r1[n%21]=0; if(n%5==0)f1[n%21]=1;
r2 = '1; f2 = '0; if(n%7==0)r2[n%23]=0; if(n%5==0)f2[n%23]=1;
r3 = '1; f3 = '0; if(n%7==0)r3[n%26]=0; if(n%5==0)f3[n%26]=1;
if(n>35)begin
if({a0,b0} !== {c0,d0})bad=bad+1;
if({a1,b1} !== {c1,d1})bad=bad+1;
if({a2,b2} !== {c2,d2})bad=bad+1;
if({a3,b3} !== {c3,d3})bad=bad+1;
end
if(n==500)begin $display("COLLECTOR_LOCKSTEP bad=%0d",bad); if(bad)$fatal(1,"collector mismatch"); $finish;end
end endmodule