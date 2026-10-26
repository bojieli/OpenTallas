`timescale 1ns/1ps
module tb;
reg ck=0,rn=0;always #5 ck=~ck;
reg[2:0]gold=0;always@(posedge ck)gold<={gold[1:0],rn};
wire[127:0]q;wire early;
ot_s81eng_reset3n32 #(.LEAVES(128))d(ck,rn,q,early);
integer i,mis=0;
initial begin
 for(i=0;i<1000;i=i+1)begin @(negedge ck);rn=(i%19>3);if(i>4&&{q,early}!=={{128{gold[2]}},gold[0]})mis=mis+1;end
 $display("RESET_TIMED %s errors=%0d assert/release=3 early=1",mis==0?"PASS":"FAIL",mis);$finish;
end
endmodule
