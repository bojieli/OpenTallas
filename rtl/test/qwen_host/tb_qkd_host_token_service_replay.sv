module tb_qkd_host_token_service_replay;
 timeunit 1ns;timeprecision 1ps;
 parameter MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg por=0,rst=0,rv=0,txcr=0;reg[511:0]rd=0;wire tx,fault;
 wire[181:0]hc;wire tev;wire[15:0]te;
 wire sb,advert,ready,abort;wire[15:0]sbe,ae,le;wire[7:0]acks;
 reg admitted_marker=0,barrier=0;integer starts=0,checks=0;
 qkd_host_service_guard guard(.ck_guard(ck),.rst_n(rst),.raw_faults(25'b0),.service_protocol_fault(1'b0),.die_id(3'd7),.physical_faults(8'b0),.transport_faults(8'b0),
 .accepted_ing_v(admitted_marker),.accepted_ing_cls(2'd0),.accepted_ing_header(16'd2),.done_v(1'b0),.done_d(64'b0),
 .boot_barrier_v(barrier),.boot_barrier_target(32'b0),.begin_v(sb),.begin_epoch(sbe),.pending_advertised(advert),.pending_epoch(ae),
 .local_tk(93'b0),.service_ready(ready),.service_epoch(le),.abort(abort));
 qkd_host_ctrl_token_service_packet #(.DIE(7),.ENABLE_TOKEN(1),.ENABLE_SERVICE(1),.MUT(MUT)) dut(
 .ck(ck),.rst_n(rst),.por_n(por),.die_id(3'd7),.rx_v(rv),.rx_d(rd),.tx_v(tx),.tx_cr(txcr),
 .local_tk(93'b0),.local_kst(10'b0),.local_boot(2'b11),.cmd_v(1'b0),.cmd_hc(182'b0),.hc(hc),.fault(fault),
 .startup_allowed(1'b1),.local_service_ready(ready),.local_service_epoch(le),.begin_v(1'b0),.begin_epoch(16'b0),
 .service_begin_v(sb),.service_begin_epoch(sbe),.pending_advertised(advert),.pending_epoch(ae),.pending_ack8(acks),
 .token_allocator_fault(1'b0),.package_abort(1'b0),.abort_drained(4'b0),.token_request_ready(1'b0),.token_grant_valid(1'b0),.token_grant_epoch(16'b0),.token_grant_token(18'b0),.token_grant_position(18'b0),.token_grant_generation(2'b0),.token_grant_tag(59'b0),
 .allocated_valid(1'b0),.allocated_delivered(1'b0),.allocated_epoch(16'b0),.allocated_token(18'b0),.allocated_position(18'b0),.allocated_generation(2'b0),.terminal_accepted(1'b0),
 .token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.token_epoch_valid(tev),.token_epoch(te));
 always @(negedge ck)begin txcr=tx;if(hc[38])begin starts++;if(!tev)$fatal(1,"missing explicit allocated epoch");end end
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task reset;begin rst=0;rv=0;admitted_marker=0;barrier=0;tick(6);rst=1;tick(20);end endtask
 task check(input bit c,input string m);begin checks++;if(!c)$fatal(1,"%s",m);end endtask
 task begin_service(input reg[15:0]e);integer n;begin
  rd=512'h80000223|(512'(e)<<48);rv=1;tick(1);rv=0;tick(25);
  check(sbe==e&&!ready&&le==e&&acks[7],"genuine addressed BEGIN/pending snapshot");
  admitted_marker=1;tick(1);admitted_marker=0;n=0;
  while(guard.mc!=1&&n<300)begin tick(1);n++;end
  check(guard.mc==1,"genuine admitted BOOT_END checkpoint");barrier=1;tick(1);barrier=0;n=0;
  while(!ready&&n<500)begin tick(1);n++;end
  tick(10);check(ready&&le==e&&!abort&&!fault,"genuine matching local barrier completes current service epoch");
 end endtask
 task start(input reg[15:0]tokenepoch,input reg[15:0]serviceepoch);reg[181:0]raw;begin
  raw=0;raw[38]=1;raw[35:18]=18'd140123;raw[17:0]=19;
  rd=512'h80000222|(512'd1<<32)|(512'(raw)<<48)|(512'(tokenepoch)<<230)|(512'd1<<246)|(512'(serviceepoch)<<247);
  rv=1;tick(1);rv=0;tick(14);
 end endtask
 initial begin
  por=0;tick(5);por=1;reset();begin_service(1);
  check(!dut.peer_epoch_seen&&starts==0,"peer never received old allocated token0");
  // The old service1/token0/seq1 start is held outside this real receiver.
  reset();begin_service(2);check(!dut.peer_epoch_seen,"token comparison history remains invalid after fresh service2");
  start(0,1);check(starts==0&&fault&&!dut.peer_epoch_seen,"never-seen stale service1/token0/seq1 cannot alias first command after service2 BEGIN0");
  reset();begin_service(3);start(0,3);check(starts==1&&!fault&&te==0,"first genuine token epoch0 valid under matching fresh service3");
  $display("PASS token service replay checks=%0d never-seen old0/service1/seq1 blocked after real service2/barrier",checks);$finish;
 end
 initial begin tick(3000);$fatal(1,"timeout");end
endmodule
