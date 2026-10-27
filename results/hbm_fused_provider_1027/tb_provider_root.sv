`timescale 1ps/1ps
module tb_provider_root;
 reg clk=0;initial forever begin #416 clk=1;#417 clk=0;end
 reg rst_n=0,load_v=0,commit=0,bound=0,start=0;reg[280:0]entry;reg[216:0]jm[0:0];
 wire jv,pdone,pfault,pbusy,armed;wire[216:0]job;wire[7:0]wsc;wire[5:0]pk5;wire pb5;
 wire rdone,rfault,rbusy;wire[172:0]dnw,dne;reg[270:0]unw=0,une=0;
 reg mutate=0;wire[216:0]delivered_job=job^(mutate?(217'd1<<5):217'd0);
 ot_hnx_fused_job217_provider provider(.clk(clk),.rst_n(rst_n),.load_v(load_v),.load_addr(8'd0),.load_entry(entry),.cfg_commit(commit),.cfg_calendar_bound(bound),.cfg_count(9'd1),.cfg_wsc(8'd24),.cfg_pk5(6'd0),.cfg_pb5(1'b0),.start(start),.job_v(jv),.job(job),.wsc(wsc),.pk5(pk5),.pb5(pb5),.root_done(rdone),.root_fault(rfault),.root_busy(rbusy),.done(pdone),.fault(pfault),.busy(pbusy),.armed(armed));
 ot_hnx_fused_hub_n4ext root(.clk(clk),.rst_n(rst_n),.job_v(jv),.job(delivered_job),.done(rdone),.fault(rfault),.busy(rbusy),.wsc(wsc),.pk5(pk5),.pb5(pb5),.up_nw(unw),.up_ne(une),.down_nw(dnw),.down_ne(dne));
 integer cc=0,start_edge=0,checks=0,errors=0,pulses=0,scalars=0,rootdones=0,pdones=0,tracehits=0,finwait=0;reg active=0;
 always @(posedge clk)begin cc<=cc+1;if(start)start_edge<=cc;end
 always @(negedge clk)if(active)begin
 checks=checks+1;
 if(jv)begin pulses=pulses+1;if(job!==jm[0]||cc-1-start_edge!=10)errors=errors+1;end
 if(root.u_native.dec)begin tracehits=tracehits+1;if(root.u_native.jq!==jm[0])errors=errors+1;end
 if(rdone)rootdones=rootdones+1;if(pdone)pdones=pdones+1;
 if(pfault)errors=errors+1;
 // Control-only leaf model: actual root SCRD commands return scalar sectors;
 // GO is acknowledged by an aligned finish. No32leaf/numeric-token claim.
 #1;unw=0;une=0;
 if(dnw[172]&&dnw[171:169]==2)begin unw={1'b1,1'b0,2'b0,dnw[168:161],3'b0,256'd0};scalars=scalars+1;end
 if(dnw[172]&&dnw[171:169]==3)finwait=5;
 if(finwait>0)begin finwait=finwait-1;if(finwait==0)begin unw={15'b000000000000110,256'd0};une=unw;end end
 end
 task automatic tick;@(negedge clk);#2;endtask
 initial begin
 $readmemh("unit_real_post_job.mem",jm);entry={32'd200,32'd10,jm[0]};mutate=$test$plusargs("MUT_JOB");
 repeat(5)tick;rst_n=1;repeat(80)tick;
 start=1;tick;start=0;repeat(5)tick;if(jv||armed)errors=errors+1;
 load_v=1;tick;load_v=0;commit=1;bound=0;tick;commit=0;if(armed)errors=errors+1;
 commit=1;bound=1;tick;commit=0;tick;if(!armed||pfault)errors=errors+1;
 active=1;start=1;tick;start=0;repeat(220)tick;active=0;
 $display("PROVIDER_ROOT_RESULT checks=%0d errors=%0d pulses=%0d scalar_returns=%0d native_trace=%0d root_done=%0d provider_done=%0d MUT_JOB=%0d clock_ps=833",checks,errors,pulses,scalars,tracehits,rootdones,pdones,mutate);
 if(errors||pulses!=1||scalars!=18||tracehits!=1||rootdones!=1||pdones!=1)$fatal(1,"PROVIDER_ROOT FAIL");
 $display("PROVIDER_ROOT PASS control-only unit calendar WSC24 PK50; current4role calendar MISSING");$finish;
 end
endmodule
