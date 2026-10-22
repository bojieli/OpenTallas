`timescale 1ns/1ps
module tb; reg clk=0; always #1 clk=~clk; reg rst_n=1,a=0; wire [1:0] q1,q2; wire z1,z2;
dut r(.clk(clk),.rst_n(rst_n),.a(a),.q(q1),.z(z1)); dut_nl n(.clk(clk),.rst_n(rst_n),.a(a),.q(q2),.z(z2));
integer i; initial begin @(negedge clk); rst_n=0; repeat(3) @(negedge clk); $display("in reset rtl %b%b nl %b%b",q1,z1,q2,z2); rst_n=1;
for(i=0;i<6;i=i+1) begin @(negedge clk); a=i[0]; $display("rtl %b%b nl %b%b",q1,z1,q2,z2); end $finish; end endmodule
