`timescale 1ns/1ps
module tb_hbm_target_participation;
reg clk=0;always #5 clk=~clk;
reg rst_n=0,cv=0,dv=0,lv=0;
reg[7:0] ct=0;
reg[11:0] ca=0,db=0;
reg[12:0] dl=1;
reg[15:0] loops=1;
wire[255:0] programme_word={16'hc7a1,4'b0,ca,224'b0};
wire[3:0] launch,conf,fault;
integer counts[0:3];
for(genvar k=0;k<2;k=k+1)begin:t
 ot_static_program_target #(.TARGET(8'(56+k)),.PCW(10)) p(.clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(ct),.cfg_addr(ca),.cfg_data(programme_word),
 .desc_v(dv),.desc_base(db),.desc_limit(dl),.desc_loops(loops),.launch_v(lv),.program_active(1'b0),
 .program_start_v(launch[k]),.configured(conf[k]),.fault(fault[k]));
 ot_static_cmd_target #(.TARGET(8'(56+k)),.MODE(0),.AWA(10),.AWB(7),.RBW(7),.RCW(8)) c(
 .clk(clk),.rst_n(rst_n),.cfg_v(cv),.cfg_target(ct),.cfg_addr(ca),.cfg_data(programme_word),.desc_v(dv),.desc_base(db),.desc_limit(dl),
 .desc_loops(loops),.launch_v(lv),.tgt_active(1'b0),.tgt_fault(1'b0),.run_v(launch[2+k]),.configured(conf[2+k]),.fault(fault[2+k]));
end
always @(posedge clk)for(integer k=0;k<4;k++)if(!rst_n)counts[k]<=0;else if(launch[k])counts[k]<=counts[k]+1;
task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
task reset;begin rst_n=0;cv=0;dv=0;lv=0;ct=0;db=0;dl=1;loops=1;repeat(3)tick;rst_n=1;repeat(3)tick;end endtask
task install(input[7:0]id);begin ct=id;cv=1;ca=0;tick;cv=0;repeat(5)tick;end endtask
task desc(input[7:0]id);begin ct=id;dv=1;tick;dv=0;repeat(4)tick;end endtask
task fire;begin lv=1;tick;lv=0;repeat(5)tick;end endtask
task no_start;begin
 if(counts[0]!=0||counts[1]!=0||counts[2]!=0||counts[3]!=0)$fatal(1,"unsafe launch counts %0d/%0d/%0d/%0d",counts[0],counts[1],counts[2],counts[3]);
 if(conf!=0)$fatal(1,"descriptor remains armed %b",conf);
end endtask
integer case_id=-1;
initial begin
 if(!$value$plusargs("CASE=%d",case_id))case_id=-1;
 if(case_id==-1||case_id==0)begin
 reset;install(56);install(57);desc(56);fire;desc(57);fire;
 if(counts[0]!=1||counts[1]!=1||counts[2]!=1||counts[3]!=1)$fatal(1,"sequential target replay counts %0d/%0d/%0d/%0d",counts[0],counts[1],counts[2],counts[3]);
 if(conf!=0||fault!=0)$fatal(1,"consumed descriptor/fault");end
 if(case_id==-1||case_id==1)begin
 reset;install(56);desc(56);ct=56;cv=1;tick;cv=0;repeat(4)tick;fire;no_start;end
 if(case_id==-1||case_id==2)begin
 reset;install(56);desc(56);dl=0;desc(56);fire;no_start;
 if(fault[0]!==1||fault[2]!==1)$fatal(1,"invalid replacement descriptor not faulted");end
 if(case_id==-1||case_id==3)begin
 reset;install(56);desc(56);ct=56;cv=1;lv=1;tick;cv=0;lv=0;repeat(5)tick;no_start;
 if(fault[0]!==1||fault[2]!==1)$fatal(1,"write/launch collision not faulted");end
 if(case_id==-1||case_id==4)begin
 reset;install(56);desc(56);ct=56;dv=1;lv=1;tick;dv=0;lv=0;repeat(5)tick;no_start;
 if(fault[0]!==1||fault[2]!==1)$fatal(1,"descriptor/launch collision not faulted");end
 if(case_id==-1||case_id==5)begin
 reset;ct=56;cv=1;dv=1;tick;cv=0;dv=0;repeat(5)tick;fire;no_start;
 if(fault[0]!==1||fault[2]!==1)$fatal(1,"write/descriptor collision not faulted");end
 $display("TARGET_PARTICIPATION PASS case=%0d sequential targets, consumed descriptor, write disarm, invalid replacement and collisions",case_id);$finish;
end
endmodule
