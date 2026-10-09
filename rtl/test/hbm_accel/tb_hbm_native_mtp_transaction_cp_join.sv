`timescale 1ns/1ps
module tb_hbm_native_mtp_transaction_cp_join;
 parameter integer MUT=0;
 reg clk=0;always #5 clk=~clk;
 reg rst_n=0,xf=0,q=0,jv=0,ready=0,cv=0,cf=0;
 reg [31:0] jid=32'habcdef10,cjid=0;reg [3:0] gen=7,cgen=0;
 reg [7:0] epoch=3,cepoch=0;reg [31:0] cseq=0;
 reg [178:0] cfg=0,provider=0;reg [516:0] fm=0;
 wire jr,v,cr,active,inflight,idfault,fault;wire [196:0] tm;reg cpav=0;reg [16:0] cpidx=17'd131071;
 wire [200:0] cmd;wire [31:0] ej,seq;wire [3:0] eg;wire [7:0] ee;
 ot_hbm_native_mtp_transaction_cp_join #(.ENABLE(1)) dut(
 .clk(clk),.rst_n(rst_n),.external_fault(xf),.backend_quiescent(q),
 .job_v(jv),.job_rdy(jr),.job_id(jid),.job_generation(gen),.job_epoch(epoch),
 .job_config(cfg),.provider_controls(provider),.f_mtp(fm),.t_mtp(tm),
 .eng_cmd_v(v),.eng_cmd_rdy(ready),.eng_cmd(cmd),.eng_job(ej),.eng_generation(eg),.eng_sequence(seq),.eng_epoch(ee),
 .cp_am_v(cpav),.cp_am_idx(cpidx),.eng_cpl_v(cv),.eng_cpl_rdy(cr),.eng_cpl_job(cjid),.eng_cpl_generation(cgen),.eng_cpl_sequence(cseq),.eng_cpl_epoch(cepoch),.eng_cpl_fault(cf),
 .active(active),.inflight(inflight),.identity_fault(idfault),.fault(fault));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task job;begin q=1;jv=1;tick();jv=0;if(!active||!tm[0])$fatal(1,"job start");tick();end endtask
 task launch;begin
 fm[82]=1;fm[83+:4]=4'hb;fm[87+:8]=8'hf1;fm[95+:4]=6;
 fm[99+:32]=32'h000fffff;fm[131+:17]=17'h1ffff;fm[148+:136]={136{1'b1}};
 repeat(30)begin tick();if(!v||tm[82]||cmd[200:65]!={136{1'b1}}||cmd[64:48]!=17'h1ffff||cmd[47:16]!=32'hfffff)$fatal(1,"full command stall");end
 ready=1;tick();ready=0;fm[82]=0;if(!inflight)$fatal(1,"accept missing");
 end endtask
 task completion;begin cjid=ej;cgen=eg;cseq=seq;cepoch=ee;cv=1;tick();cv=0;end endtask
 initial begin
 tick();rst_n=1;tick();jv=1;tick();if(jr||active)$fatal(1,"unquiesced admission");jv=0;
 cfg[6+:21]=21'h100000;cfg[27+:21]=21'hfffff;provider[139]=1;
 job();launch();cjid=ej;cgen=eg;cseq=seq;cepoch=ee;cpav=1;tick();
 if(!tm[179]||tm[196:180]!=131071)$fatal(1,"owned AM forwarding");cpav=0;completion();if(!tm[83]||inflight||fault)$fatal(1,"owned completion");
 tick();if(tm[83])$fatal(1,"done duplicated");
 launch();cjid=ej;cgen=eg;cseq=seq;cepoch=ee+1;cv=1;tick();cv=0;
 if(!fault||!idfault||tm[83]||tm[139])$fatal(1,"stale epoch accepted");
 completion();if(tm[83]||!fault)$fatal(1,"faulted command later completed");
 xf=1;tick();xf=0;q=0;jv=1;tick();jv=0;if(active)$fatal(1,"fault without quiescence");
 epoch=4;job();launch();
 if(MUT)begin cjid=ej;cgen=eg;cseq=seq;cepoch=ee-1;cv=1;tick();cv=0;
  if(tm[83])$display("BAD completion accepted");else $fatal(1,"golden rejects stale response");end
 completion();if(!tm[83]||fault)$fatal(1,"restart identity");tick();fm[81]=1;tick();fm[81]=0;
 if(active)$fatal(1,"native done");
 // Reset while command is owned. New epoch must reject old response.
 epoch=5;job();launch();rst_n=0;tick();rst_n=1;q=0;tick();if(jr)$fatal(1,"reset quiescence");
 epoch=6;job();launch();cjid=ej;cgen=eg;cseq=seq;cepoch=5;cv=1;tick();cv=0;
 if(!fault||!idfault||tm[83])$fatal(1,"reset stale response");
 xf=1;tick();xf=0;epoch=7;job();launch();
 cjid=ej;cgen=eg;cseq=seq;cepoch=ee-1;cpav=1;#1;if(tm[179])$fatal(1,"stale AM forwarded before pin capture");tick();
 if(tm[179]||!fault||!idfault)$fatal(1,"stale AM accepted");
 $display("PASS full201 command, owned TOKEN17 AM197, backpressure, fault, reset epoch");$finish;
 end
endmodule
