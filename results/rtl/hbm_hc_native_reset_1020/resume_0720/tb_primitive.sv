`timescale 1ns/1ps
module tb_primitive;
reg clk=0,d=0,rn=0,sn=1;wire qn;
DFFASRHQNx1_ASAP7_75t_R u(.CLK(clk),.D(d),.RESETN(rn),.SETN(sn),.QN(qn));
integer checks=0,errors=0;
task check(input bit want);begin checks=checks+1;if(qn!==want)begin errors=errors+1;$display("ASYNC_COUPON_MISMATCH t=%0t qn=%b want=%b",$time,qn,want);end end endtask
initial begin
// Held low from elaboration and stopped clock: Liberty preset !RESETN dominates.
#0.1;check(1);#0.2;check(1);
// Explicit assertion and all clear/preset combinations, still stopped clock.
rn=1;#0.1;rn=0;#0.1;check(1);sn=0;#0.1;check(0);rn=1;#0.1;check(0);sn=1;#0.1;
d=0;clk=1;#0.1;check(1);clk=0;#0.1;d=1;clk=1;#0.1;check(0);
if(errors==0)$display("ASYNC_COUPON PASS checks=%0d",checks);else $display("ASYNC_COUPON FAIL errors=%0d checks=%0d",errors,checks);$finish;
end
endmodule
