module tb_qkd_host_token_replay;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg por=0,rst=0,rv=0,wv=0,wd=0,wr=0,wt=0,txcr=0;reg[511:0]rd=0;
 wire[181:0]hc;wire tev,fault,tx;wire[15:0]epoch;integer starts=0,checks=0;
 qkd_host_ctrl_token_service_packet #(.DIE(7),.ENABLE_TOKEN(1),.MUT(MUT)) dut(
 .ck(ck),.rst_n(rst),.por_n(por),.die_id(3'd7),.rx_v(rv),.rx_d(rd),.tx_v(tx),.tx_cr(txcr),
 .local_tk({1'b1,2'b0,1'b1,89'b0}),.local_kst(10'b0),.local_boot(2'b11),.cmd_v(1'b0),.cmd_hc(182'b0),.hc(hc),.fault(fault),
 .startup_allowed(1'b1),.local_service_ready(1'b1),.local_service_epoch(16'b0),.begin_v(1'b0),.begin_epoch(16'b0),
 .token_allocator_fault(1'b0),.package_abort(1'b0),.abort_drained(4'b0),.token_request_ready(1'b0),.token_grant_valid(1'b0),.token_grant_epoch(16'b0),.token_grant_token(18'b0),.token_grant_position(18'b0),.token_grant_generation(2'b0),.token_grant_tag(59'b0),
 .allocated_valid(1'b0),.allocated_delivered(1'b0),.allocated_epoch(16'b0),.allocated_token(18'b0),.allocated_position(18'b0),.allocated_generation(2'b0),.terminal_accepted(1'b0),
 .token_wrap_fence_valid(wv),.token_wrap_drained(wd),.token_wrap_link_reset_seen(wr),.token_wrap_retraining_done(wt),.token_epoch_valid(tev),.token_epoch(epoch));
 always @(negedge ck)begin txcr=tx;if(hc[38])begin starts++;if(!tev)$fatal(1,"received start missing explicit token epoch");end end
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task reset;begin rst=0;rv=0;wv=0;wd=0;wr=0;wt=0;tick(5);rst=1;tick(10);end endtask
 task start(input reg[15:0]e,input reg[15:0]seq);reg[181:0]raw;begin
 raw=0;raw[38]=1;raw[35:18]=18'd140123;raw[17:0]=19;raw[37:36]=0;
 rd=512'h80000222|(512'(seq)<<32)|(512'(raw)<<48)|(512'(e)<<230)|(512'd1<<246);rv=1;tick(1);rv=0;tick(12);
 end endtask
 task check(input bit c,input string m);begin checks++;if(!c)$fatal(1,"%s",m);end endtask
 initial begin
 por=0;tick(5);por=1;reset();start(0,0);$display("TRACE replay starts%0d fault%b epoch%0d lastvalid%b last%0d seqseen%h",starts,fault,epoch,dut.peer_epoch_seen,dut.peer_last_epoch,dut.seq_seen);check(starts==1&&!fault&&epoch==0,"initial allocated token epoch0 valid");
 reset();start(0,0);check(starts==1&&fault,"soft reset cannot accept delayed old native epoch0 seq0/gen0");
 reset();start(1,0);check(starts==2&&!fault&&epoch==1,"fresh central epoch1 allowed after reset");
 reset();start(0,0);check(starts==2&&fault,"older epoch rejected despite reset sequence rearm");
 reset();wv=1;wd=1;wr=1;wt=0;tick(1);wv=0;tick(8);check(fault,"incomplete actual retraining proof cannot reset witness");
 reset();wv=1;wd=1;wr=1;wt=1;tick(1);wv=0;tick(8);start(0,0);
 check(starts==3&&!fault,"explicit all-peer wrap/drain/link-reset/retrain fence permits reused epoch0");
 $display("PASS token replay checks=%0d PORretained initial0/stale0/new1/wrap",checks);$finish;
 end
 initial begin tick(1000);$fatal(1,"timeout");end
endmodule
