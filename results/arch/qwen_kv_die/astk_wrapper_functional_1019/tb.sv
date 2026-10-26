`timescale 1ns/1ps
module tb;
reg ck=0,rst_n=1;reg[295:0] a=0;wire[295:0] qn,q0,qd,qm;
qkd_astk_rly_296_fl_native n(ck,rst_n,a,qn);
qkd_astk_rly_296_fl #(.MUT(0)) z(ck,rst_n,a,q0);
qkd_astk_rly_296_fl d(ck,rst_n,a,qd);
qkd_astk_rly_296_fl #(.MUT(1)) m(ck,rst_n,a,qm);
integer i,checks=0,seen=0;
task verify;begin
 if(qn !== q0 || q0 !== qd) begin $display("FAIL native/default/MUT0 data=%h/%h/%h",qn,q0,qd);$fatal(1);end
 checks=checks+296;
end endtask
initial begin
 #1;rst_n=0;#1;verify;
 #1;rst_n=1;a={296{1'b1}};
 #1;ck=1;#1;verify;
 if(qm!==a || qn!==296'd0) $fatal(1,"MUT1 expected causal release-bypass discrepancy absent");
 $display("MUT1_CAUSAL_CEX t=%0t after first release edge: native=%h default=%h MUT0=%h MUT1=%h",$time,qn,qd,q0,qm);seen=1;
 for(i=0;i<80;i=i+1) begin
  ck=0; a={$random,$random,$random,$random,$random,$random,$random,$random,$random,$random};
  #1;if(i%11==0)rst_n=0;#1;verify;
  if(i%11==1)rst_n=1;
  #1;ck=1;#1;verify;
 end
 if(!seen)$fatal(1,"missing actual MUT1 witness");
 $display("PASS NATIVE_WRAPPER checks=%0d all296 outputs compared, startup+reassert+release histories",checks);
 $finish;
end
endmodule
