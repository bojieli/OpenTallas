module ot_dp_st #(parameter integer W=1)(input wire clk,rst_n,input wire[W-1:0]d,input wire ea,output reg[W-1:0]q,output reg eq);
 always @(posedge clk)q<=d;
 always @(posedge clk or negedge rst_n)if(!rst_n)eq<=0;else eq<=ea;
endmodule
module tb;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,d=0,ea=0;wire oldq,olde,q0,q1,q2,e0,e1,e2;
ot_dp_st face(.clk(clk),.rst_n(rst_n),.d(d),.ea(ea),.q(oldq),.eq(olde));
ot_dp_st st0(.clk(clk),.rst_n(rst_n),.d(oldq),.ea(olde),.q(q0),.eq(e0));
ot_dp_st st1(.clk(clk),.rst_n(rst_n),.d(q0),.ea(e0),.q(q1),.eq(e1));
ot_dp_st st2(.clk(clk),.rst_n(rst_n),.d(q1),.ea(e1),.q(q2),.eq(e2));
reg[2:0]dq,eqh;always @(posedge clk)dq<={dq[1:0],oldq};always @(posedge clk or negedge rst_n)if(!rst_n)eqh<=0;else eqh<={eqh[1:0],olde};
`ifdef MUTANT
 wire observed=q1;
`else
 wire observed=q2;
`endif
integer n=0;always @(negedge clk)begin n=n+1;rst_n=(n%31)>3;d=(n%7)<3;ea=(n%5)<2;end
always @(posedge clk)begin #1;if(n>8&&({observed,e2}!=={dq[2],eqh[2]}))$fatal(1,"MISMATCH resetbus+3cycles n%0d",n);if(n>1000)begin $display("PASS3resetbuscycles1000edges,payload+epoch,repeatreset");$finish;end end
endmodule
