`timescale 1ns/1ps
module tb;
reg ck=0;always #5 ck=~ck;
reg d=0,rst=0,pre=0;
wire q,qref,a,aref,b,bref;
DFFHQNx1_ASAP7_75t_R f(q,d,ck);
native_DFFHQNx1_ASAP7_75t_R fr(qref,d,ck);
DFFASRHQNx1_ASAP7_75t_R ar(a,d,rst,1'b1,ck);
native_DFFASRHQNx1_ASAP7_75t_R arr(aref,d,rst,1'b1,ck);
DFFASRHQNx1_ASAP7_75t_R br(b,d,1'b1,pre,ck);
native_DFFASRHQNx1_ASAP7_75t_R brr(bref,d,1'b1,pre,ck);
integer i;
task check;begin if({q,a,b}!=={qref,aref,bref})$fatal(1,"FF_MODEL_MISMATCH i%0d",i);end endtask
initial begin
for(i=0;i<300;i=i+1)begin
@(negedge ck);#1;rst=(i%7>1);pre=(i%11>2);case(i%3)0:d=0;1:d=1;2:d=1'bx;endcase
#1;check();@(posedge ck);#1;check();end
$display("FF_MODELS_PASS 600checks binary independentclear/preset+Xdata, exact actualshape asyncbinding");$finish;end
endmodule
