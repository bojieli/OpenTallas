`timescale 1ns/1ps
module tb_pv_den_stamp;
 reg clk=0;always #0.5 clk=~clk;reg rn=0,cv=0,op=0,den=1,err=0;reg[3:0]kind=4;reg[7:0]oj=8'h31,rj=8'h31;
 reg[19:0]owner=20'h92345;reg[512:0]d;wire[512:0]s,s0;
 dsdv_pv_den_stamp #(.ENABLE(1))dut(.clk(clk),.rst_n(rn),.cfg_v(cv),.cfg_owner(owner),.cfg_se_jid(8'h31),.op_st(op),.op_kind(kind),.op_jid(oj),.den(den),.result_jid(rj),.error(err),.pv_d(d),.stamped(s));
 dsdv_pv_den_stamp off(.clk(clk),.rst_n(rn),.cfg_v(cv),.cfg_owner(owner),.cfg_se_jid(8'h31),.op_st(op),.op_kind(kind),.op_jid(oj),.den(den),.result_jid(rj),.error(err),.pv_d(d),.stamped(s0));
 task tick;@(negedge clk);#0.01;endtask
 task proof(input bit want,input[255:0]why);begin #0.01;if(s[120]!==want)$fatal(1,"DEN_STAMP %s",why);if(s0!==d)$fatal(1,"DEN_DEFAULT_CHANGED");end endtask
 initial begin
 d=0;d[512]=1;d[91:72]=owner;repeat(4)tick();rn=1;cv=1;tick();cv=0;op=1;tick();op=0;repeat(3)tick();proof(0,"stalehigh afterSEstart");
 den=0;tick();den=1;rj=8'h32;tick();proof(0,"wrongjid");rj=8'h31;tick();proof(1,"actualSEden");
 d[91:72]=owner^1;proof(0,"wrongowner");d[91:72]=owner;proof(1,"ownerrestored");
 cv=1;tick();cv=0;op=1;tick();op=0;repeat(3)tick();proof(0,"reusedjid stalehigh");
 den=0;tick();den=1;err=1;tick();proof(0,"actualSMerror");err=0;tick();proof(1,"cleangenuinecompletion");
 rn=0;tick();rn=1;proof(0,"resetstale");
 d[512]=0;d[128:120]=9'h1ff;#0.01;if(s!==d)$fatal(1,"DEN_PAYLOAD_CHANGED");
 $display("DEN_STAMP_PASS actualSE low-to-high jid owner reusedjid reset error payload default0");$finish;
 end
endmodule
