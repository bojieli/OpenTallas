`timescale 1ns/1ps
module tb_truth;
reg clk=0,d=0,rn=1,sn=1;wire q;
DFFASRHQNx1_ASAP7_75t_R dut(.CLK(clk),.D(d),.QN(q),.RESETN(rn),.SETN(sn));
integer checks=0;
task check(input expected);begin #1;if(q!==expected)$fatal(1,"ASR_TRUTH expected=%b got=%b clk=%b d=%b rn=%b sn=%b",expected,q,clk,d,rn,sn);checks=checks+1;end endtask
task capture(input data);begin clk=0;d=data;#1;clk=1;check(~data);clk=0;#1;end endtask
initial begin
 #1;rn=0;check(1);d=1;check(1);rn=1;check(1);capture(1);capture(0);
 sn=0;check(0);d=0;check(0);sn=1;check(0);capture(0);capture(1);
 rn=0;check(1);sn=0;check(0);sn=1;check(1);rn=1;check(1);capture(1);
 sn=0;rn=0;check(0);rn=1;check(0);sn=1;check(0);capture(0);
 rn=0;sn=0;check(0);rn=1;sn=1;check(0);capture(1);capture(0);
 $display("ASR_LIB_TRUTH_PASS checks=%0d",checks);$finish;
end
endmodule
