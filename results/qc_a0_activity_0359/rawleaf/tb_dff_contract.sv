`timescale 1ns/1ps
module tb_dff_contract;
reg CLK=0,D=0,RESETN=1,SETN=1;wire QN;integer checks=0;
DFFASRHQNx1_ASAP7_75t_R dut(.*);
task check(input bit v);begin #1;if(QN!==v)$fatal(1,"ASRHQN actuallib mismatch got%b expected%b",QN,v);checks=checks+1;end endtask
initial begin
#1;CLK=1;check(1);CLK=0;D=1;#1;CLK=1;check(0);CLK=0;
RESETN=0;check(1);RESETN=1;check(1);SETN=0;check(0);RESETN=0;check(0);
CLK=1;check(0);CLK=0;RESETN=1;SETN=1;D=0;#1;CLK=1;check(1);
$display("ASRHQN_ACTUAL_LIB_PASS checks=%0d next=!D preset=!RESETN clear=!SETN both=L",checks);$finish;
end
endmodule
