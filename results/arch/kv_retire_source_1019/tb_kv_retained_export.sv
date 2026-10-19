module tb_kv_retained_export;
 timeunit 1ns;timeprecision 1ps;
 parameter integer MUT=0,EXPORT_MUT=0;
 reg por=0;wire retained,guard_abort;wire[92:0]guard_tk;wire[31:0]guard_status;wire guard_ready;
 reg ck=0;always #0.4165 ck=~ck;
 reg rst=0,cmd=0,abort=0,rr=0,gv=0,av=0,ad=0,ack=0;reg[3:0]drains=0;
 reg[181:0]raw=0;reg[15:0]ge=0;reg[17:0]gt=0,gp=0;reg[1:0]gg=0;reg[58:0]tag=0;
 wire tx,cr,req,gr,tev,cv,cd,cf,ff;wire[511:0]packet;wire[181:0]hc;
 wire[17:0]rt,rp;wire[1:0]rg,cgen;wire[15:0]epoch;wire[58:0]ctag;wire[3:0]cda;
 reg txcredit=0;integer local_starts=0,packets=0,requests=0,credits=0,checks=0;
 reg req_last=0;reg[181:0]expected;integer scenario=0;
 `ifdef TEST_MU
 qkd_host_ctrl_token_service_packet_collected_mu_rh #(
`else
 qkd_host_ctrl_token_service_packet_collected_rh #(
`endif
.DIE(0),.ENABLE_TOKEN(1),.MUT(MUT)) dut(
 .ck(ck),.rst_n(rst),.die_id(3'd0),.rx_v(1'b0),.rx_d(512'd0),.tx_v(tx),.tx_d(packet),.tx_cr(txcredit),
 .local_tk(93'd0),.local_kst(10'd0),.local_boot(2'd3),.cmd_v(cmd),.cmd_hc(raw),.cmd_cr(cr),.hc(hc),.fault(ff),
 .startup_allowed(1'b1),.local_service_ready(1'b1),.local_service_epoch(16'd0),.begin_v(1'b0),.begin_epoch(16'd0),
 .por_n(por),.retained_context(retained),.token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.token_allocator_fault(1'b0),.package_abort(abort),.abort_drained(drains),.token_request_valid(req),.token_request_ready(rr),
 .token_request_token(rt),.token_request_position(rp),.token_request_generation(rg),
 .token_grant_valid(gv),.token_grant_ready(gr),.token_grant_epoch(ge),.token_grant_token(gt),
 .token_grant_position(gp),.token_grant_generation(gg),.token_grant_tag(tag),
 .allocated_valid(av),.allocated_delivered(ad),.allocated_epoch(ge),.allocated_token(gt),.allocated_position(gp),.allocated_generation(gg),
 .token_epoch_valid(tev),.token_epoch(epoch),.cancel_valid(cv),.cancel_tag(ctag),.cancel_generation(cgen),
 .cancel_done(cd),.cancel_fault(cf),.cancel_drained(cda),.terminal_accepted(ack));
 qkd_host_service_guard_wh guard(.ck_guard(ck),.rst_n(rst),.por_n(por),.raw_faults(25'd0),
 .retained_ctx(EXPORT_MUT==1?1'b0:retained),.recovery_certified(1'b0),.die_id(3'd0),
 .physical_faults(8'd0),.transport_faults(8'd0),.accepted_ing_v(1'b0),.accepted_ing_cls(2'd0),
 .accepted_ing_header(16'd0),.done_v(1'b0),.done_d(64'd0),.boot_barrier_v(1'b0),
 .boot_barrier_target(32'd0),.begin_v(1'b0),.begin_epoch(16'd0),.pending_advertised(1'b0),
 .pending_epoch(16'd0),.local_tk(93'd0),.guarded_tk(guard_tk),.abort(guard_abort),
 .service_ready(guard_ready),.status(guard_status),.service_protocol_fault(1'b0));
 always @(negedge ck) if(por)begin
 `ifdef TEST_MU
  if(retained !== (|dut.g_mu.rr))$fatal(1,"MU_EXPORT_MISMATCH");
 `else
  if(retained !== dut.retained_request)$fatal(1,"SU_EXPORT_MISMATCH");
 `endif
 end
 always @(negedge ck)begin
  txcredit<=tx;
  if(rst)begin
   if(req&&!req_last)requests=requests+1;req_last=req;
   if(hc[38])begin
    local_starts=local_starts+1;
    if(abort||!tev||hc!==expected||epoch!==ge)$fatal(1,"local grant/abort/payload identity");
   end
   if(tx)begin
    packets=packets+1;
    if(packet[7:0]!==8'h22||packet[229:48]!==expected)$fatal(1,"peer HC payload");
    if(expected[38])begin
     if(packet[15:8]!==2||!packet[246]||packet[245:230]!==ge)$fatal(1,"peer epoch/valid");
    end else if(packet[15:8]!==1||packet[511:230]!==0)$fatal(1,"metadata must have no token epoch");
   end
   if(cr)credits=credits+1;
  end
 end
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 task check(input bit condition,input string msg);begin checks++;if(!condition)$fatal(1,"%s",msg);end endtask
 task reset;begin por=0;rst=0;cmd=0;gv=0;av=0;rr=0;ack=0;abort=0;drains=0;tick(6);por=1;rst=1;tick(8);end endtask
 task sendhc(input reg[181:0]h);begin raw=h;expected=h;cmd=1;tick(1);cmd=0;tick(6);end endtask
 task grant(input reg[15:0]e,input bit bad);begin
  ge=e;gt=rt+(bad?1:0);gp=rp;gg=rg;tag={e,6'd0,gt,gp[12:0],6'd0};av=1;rr=1;tick(4);rr=0;
  gv=1;tick(6);gv=0;tick(30);
 end endtask
 initial begin
 reset();expected=182'd0;expected[38]=1;expected[35:18]=18'd140123;expected[17:0]=18'd8191;expected[37:36]=2;
 expected[113]=1;expected[181]=1;expected[112:39]=74'h123456789abcdef123;
 sendhc(expected);check(req&&rt==140123&&rp==8191&&rg==2,"each genuine HC start must request allocator");
 tick(20);check(local_starts==0&&packets==0,"no command before held matching grant");
 grant(0,0);check(local_starts==1&&packets==7&&credits==1&&!ff,"epoch0 allocated full seven copies + local");
 expected=0;expected[113]=1;expected[112:39]=74'h2abc;sendhc(expected);tick(40);
 check(requests==1&&packets==14&&credits==2&&!ff,"metadata order, no duplicate allocation");
 expected=0;expected[38]=1;expected[35:18]=18'd131111;expected[17:0]=18'd123;expected[37:36]=3;sendhc(expected);
 check(requests==2,"every auto decode step independently requests allocator");grant(16'd19,0);
 check(local_starts==2&&packets==21&&credits==3&&!ff,"second matching allocated identity");
 reset();local_starts=0;packets=0;credits=0;requests=0;req_last=0;
 expected=0;expected[38]=1;expected[35:18]=1234;expected[17:0]=33;sendhc(expected);grant(3,1);
 check(ff&&local_starts==0&&packets==0,"mismatching grant fail closed");
 reset();local_starts=0;packets=0;credits=0;requests=0;req_last=0;
 expected=0;expected[38]=1;expected[35:18]=7890;expected[17:0]=55;expected[37:36]=1;sendhc(expected);
 ge=16'd23;gt=rt;gp=rp;gg=rg;tag={ge,6'd0,gt,gp[12:0],6'd0};av=1;rr=1;tick(4);rr=0;
 abort=1;tick(8);check(!cv&&local_starts==0&&packets==0,"abort with hidden grant cannot launch or invent drained");
 gv=1;tick(10);check(!gr&&local_starts==0&&packets==0,"delayed grant after abort forbidden");gv=0;
 drains=4'b0111;tick(8);check(!cv,"missing HOST drain cannot retire allocation");drains=15;tick(8);
 check(cv&&cf&&!cd&&cda==15&&ctag=={16'd23,6'd37,18'd7890,13'd55,6'd0}&&cgen==1,"genuine allocated fault-terminal exact identity");
 tick(8);check(cv,"cancel held until registered allocator acknowledgment");ack=1;tick(4);ack=0;tick(8);
 check(!cv&&local_starts==0&&packets==0,"cancel consumed once no start");
 // The original transport scenarios above are unchanged. Add a genuine
 // accepted request/grant, then warm reset with POR deliberately still high.
 reset();local_starts=0;packets=0;credits=0;requests=0;req_last=0;
 expected=0;expected[38]=1;expected[35:18]=991;expected[17:0]=55;
 sendhc(expected);grant(27,0);check(retained,"REAL_REQUEST_NOT_RETAINED");
 check(!guard_abort,"unexpected guard health before warm reset");
 rst=0;cmd=0;tick(3);check(retained,"WARM_RESET_LOST_POR_CONTEXT");
 check(guard_abort&&guard_tk[88]&&guard_status[2],"WARM_RETAINED_VETO_MISSING");
 rst=1;tick(12);check(guard_abort&&!guard_ready,"WARM_RETAINED_VETO_REOPENED");
 por=0;tick(3);check(!retained,"POR_DID_NOT_CLEAR_EXPORT");
 $display("KV_RETAINED_EXPORT_PASS checks=%0d actual request/grant/cancel, warm/POR, guard veto",checks);$finish;
 end
 initial begin tick(2000);$fatal(1,"timeout");end
endmodule
