`timescale 1ns/1ps
module tb_qwen_su_source_observer;
 reg ck=0;always #1 ck=~ck;
 reg rn=0,issue=0,candidate=0;reg[1:0]unit=2;reg[11:0]base=14,pc=3;wire[15:0]observe;
 ot_qfd_su_source_observer dut(.clk(ck),.rst_n(rn),.issue(issue),.candidate_v(candidate),.unit(unit),.program_base(base),.candidate_pc(pc),.observe(observe));
 initial begin
 repeat(2)@(negedge ck);rn=1;issue=1;candidate=1;
 @(posedge ck);#0.01;if(observe!==16'he011)$fatal(1,"actual segment PC/owner missing");
 @(negedge ck);pc=4;
 #0.01;if(observe!==16'he011)$fatal(1,"observer did not retain pin register");
 @(posedge ck);#0.01;if(observe!==16'he012)$fatal(1,"actual candidate PC lost");
 @(negedge ck);candidate=0;
 @(posedge ck);#0.01;if(observe!==16'ha012)$fatal(1,"candidate availability hid scheduled source issue");
 @(negedge ck);issue=0;pc=5;
 @(posedge ck);#0.01;if(observe[15]!==0||observe[11:0]!==19)$fatal(1,"idle generated phantom source issue");
 @(negedge ck);rn=0;#0.01;if(observe!==0)$fatal(1,"source pin reset");
 $display("PASS actual SU source observer relative PC, registered edge, missingcandidate and no phantom issue");$finish;
 end
endmodule
