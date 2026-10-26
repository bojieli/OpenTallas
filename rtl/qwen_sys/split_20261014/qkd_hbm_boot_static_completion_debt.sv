`timescale 1ns/1ps
// Boot switch plus actual launched-command owner observation. Normal responses
// are gated until boot data checks AND all four physical retirements are seen.
// Added completion routing latency is one ck cycle; command path remains +1 ck.
module qkd_hbm_boot_static_completion_debt #(parameter integer TIMEOUT=20000,MUT=0)(
 input wire ck,ck_test,rst_n,boot_go,
 input wire[287:0]normal_es,output wire[260:0]normal_er,
 output wire[287:0]ctrl_es,input wire[260:0]ctrl_er,
 input wire completion_v,completion_we,
 output wire normal_completion_v,normal_completion_we,
 output wire boot_completion_v,boot_completion_we,
 output wire boot_done,boot_ok,output wire[3:0]boot_cause,
 output wire fault,output reg boot_quiet);
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)boot_quiet<=0;
  else boot_quiet<=(MUT==2)?(test_done&&test_ok&&!fault):verified&&test_done&&test_ok&&empty&&!waiting&&!boot_go&&
   !normal_es[0]&&!ctrl_es[0]&&!ctrl_er[0]&&!ctrl_er[259]&&!ctrl_er[260]&&
   !completion_v&&!normal_completion_v&&!boot_completion_v&&!raw_normal_er[0]&&!fault;
 end
 wire test_done,test_ok,base_fault,demux_fault,empty;wire[260:0]raw_normal_er;
 reg launch_boot;reg[2:0]retired;reg check_fault,verified;reg waiting;reg[31:0]timer;
 wire qualified=verified&&!fault;
 assign boot_done=test_done&&(test_ok?verified:1'b1);
 assign boot_ok=qualified;assign normal_er=qualified?raw_normal_er:261'b0;
 assign fault=base_fault|demux_fault|check_fault;
 qkd_hbm_boot_static #(.TIMEOUT(TIMEOUT))u_boot(.ck(ck),.ck_test(ck_test),.rst_n(rst_n),.boot_go(boot_go),
  .normal_es(qualified?normal_es:288'b0),.normal_er(raw_normal_er),.ctrl_es(ctrl_es),.ctrl_er(ctrl_er),
  .boot_done(test_done),.boot_ok(test_ok),.boot_cause(boot_cause),.fault(base_fault));
 // Matches the registered choice which produces ctrl_es on the same edge.
 always @(posedge ck or negedge rst_n)if(!rst_n)launch_boot<=1;else launch_boot<=!(test_done&&test_ok);
 qkd_static_completion_ownerdemux #(.MUT(MUT))u_owner(.ck(ck),.rst_n(rst_n),.launch_v(ctrl_es[0]),.launch_boot(launch_boot),.launch_we(ctrl_es[286]),
  .completion_v(completion_v),.completion_we(completion_we),.normal_completion_v(normal_completion_v),.normal_completion_we(normal_completion_we),
  .boot_completion_v(boot_completion_v),.boot_completion_we(boot_completion_we),.fault(demux_fault),.empty(empty));
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin retired<=0;check_fault<=0;verified<=0;waiting<=0;timer<=0;end
  else begin
   if(waiting&&!verified)begin timer<=timer+1'b1;if(timer>=TIMEOUT)check_fault<=1;end
   if(test_done&&test_ok&&retired==4&&empty&&!fault)begin verified<=1;waiting<=0;end
   if(boot_go)begin waiting<=1;timer<=0;if(!empty||retired!=0)check_fault<=1;end
   if(!qualified&&normal_es[0])check_fault<=1;
   if(boot_completion_v)begin
    if(retired==4||boot_completion_we!=!retired[0])check_fault<=1;
    else retired<=retired+1'b1;
   end
  end
 end
endmodule
