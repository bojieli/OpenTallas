`timescale 1ns/1ps
module tb;
reg clk=0;always #5 clk=~clk;
reg rst=0;reg[132:0] d=0;wire[7:0] q1;wire[132:0]q2;
reg[132:0] hist[0:1199];integer n,k,checked=0;
ot_qc_su_mem9_qfd_dv_s1_delay #(.W(8),.D(58),.FLOP(1),.SEGMENTED(1)) s1(clk,rst,rst,d[7:0],q1);
ot_qc_su_mem9_qfd_dv_s1_delay #(.W(133),.D(60),.FLOP(1),.SEGMENTED(1)) s2(clk,rst,rst,d,q2);
initial begin
for(n=0;n<1200;n=n+1) begin
@(negedge clk);
if(n==20) rst=1;
d={$random,$random,$random,$random,5'b10101};
hist[n]=d;
@(posedge clk); #1;
if(n>100) begin
if(q1!==hist[n-57][7:0]) $fatal(1,"S1 bad n%0d got%h exp%h",n,q1,hist[n-57][7:0]);
if(q2!==hist[n-59]) $fatal(1,"S2 bad n%0d got%h exp%h",n,q2,hist[n-59]);
checked=checked+1;
end
end
$display("PASS checked=%0d S1=58 S2=60 all133bits",checked);$finish;
end
endmodule
