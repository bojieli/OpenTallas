module tb_qkd_host_token_allocator_transport;
 timeunit 1ns;timeprecision 1ps;
 parameter integer MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg por=0,warm=1;reg rst=0,cmd=0,abort=0;wire rr,gv,av,ad,ack;reg[3:0]drains=0;
 reg[181:0]raw=0;wire[15:0]ge;wire[17:0]gt,gp;wire[1:0]gg;wire[58:0]tag;wire allocfault,allocbusy;
 wire tx,cr,req,gr,tev,cv,cd,cf,ff;wire[511:0]packet;wire[181:0]hc;
 wire[17:0]rt,rp;wire[1:0]rg,cgen;wire[15:0]epoch;wire[58:0]ctag;wire[3:0]cda;
 reg txcredit=0;integer local_starts=0,packets=0,requests=0,credits=0,checks=0;
 reg req_last=0;reg[181:0]expected;integer scenario=0;
 qkd_host_ctrl_token_service_packet #(.DIE(0),.ENABLE_TOKEN(1),.MUT(MUT)) dut(
 .ck(ck),.rst_n(rst),.die_id(3'd0),.rx_v(1'b0),.rx_d(512'd0),.tx_v(tx),.tx_d(packet),.tx_cr(txcredit),
 .local_tk(93'd0),.local_kst(10'd0),.local_boot(2'd3),.cmd_v(cmd),.cmd_hc(raw),.cmd_cr(cr),.hc(hc),.fault(ff),
 .startup_allowed(1'b1),.local_service_ready(1'b1),.local_service_epoch(16'd0),.begin_v(1'b0),.begin_epoch(16'd0),
 .por_n(por),.token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.package_abort(abort),.abort_drained(drains),.token_request_valid(req),.token_request_ready(rr),
 .token_request_token(rt),.token_request_position(rp),.token_request_generation(rg),
 .token_grant_valid(gv),.token_grant_ready(gr),.token_grant_epoch(ge),.token_grant_token(gt),
 .token_grant_position(gp),.token_grant_generation(gg),.token_grant_tag(tag),
 .allocated_valid(av),.allocated_delivered(ad),.allocated_epoch(ge),.allocated_token(gt),.allocated_position(gp),.allocated_generation(gg),
 .token_epoch_valid(tev),.token_epoch(epoch),.cancel_valid(cv),.cancel_tag(ctag),.cancel_generation(cgen),
 .cancel_done(cd),.cancel_fault(cf),.cancel_drained(cda),.terminal_accepted(ack));
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
 task reset;begin rst=0;cmd=0;abort=0;drains=0;tick(6);rst=1;tick(8);end endtask
 task sendhc(input reg[181:0]h);begin raw=h;expected=h;cmd=1;tick(1);cmd=0;tick(6);end endtask
 ot_qwen_tp8_token_epoch_allocator allocator(.clk(ck),.por_n(por),.warm_ready(warm),
 .request_valid(req),.request_ready(rr),.request_token(rt),.request_position(rp),.request_generation(rg),
 .grant_valid(gv),.grant_ready(gr),.grant_epoch(ge),.grant_token(gt),.grant_position(gp),.grant_generation(gg),.grant_tag(tag),
 .allocated_valid(av),.allocated_delivered(ad),.terminal_valid(cv),.terminal_tag(ctag),.terminal_generation(cgen),
 .terminal_done(cd),.terminal_fault(cf),.terminal_kv_drained(cda[0]),.terminal_vm_drained(cda[1]),
 .terminal_collective_drained(cda[2]),.terminal_host_drained(cda[3]),
 .wrap_fence_valid(1'b0),.wrap_links_drained(1'b0),.wrap_link_reset_seen(1'b0),.wrap_retraining_done(1'b0),
 .busy(allocbusy),.identity_fault(allocfault),.terminal_accepted(ack));
 initial begin
 por=0;tick(5);por=1;reset();
 expected=0;expected[38]=1;expected[35:18]=18'd140123;expected[17:0]=18'd8191;expected[37:36]=2;
 sendhc(expected);tick(45);
 check(local_starts==1&&packets==7&&credits==1&&ad&&!allocfault&&!ff&&ge==0,"actual initial allocated epoch0 full broadcast");
 // Genuine abort after command delivery still retains identity even though
 // the seven-copy scheduler returned its source credit.
 abort=1;drains=4'b0111;tick(12);check(allocbusy&&!cv,"incomplete real drains must keep allocated identity");
 drains=15;tick(18);check(!allocbusy&&!cv&&!allocfault,"actual registered fault-terminal consumes once and re-arms");
 reset();local_starts=0;packets=0;credits=0;requests=0;req_last=0;
 // Force warm gating off immediately after real request acceptance. The
 // allocation witness remains genuine while the delivery valid is hidden.
 expected=0;expected[38]=1;expected[35:18]=18'd131111;expected[17:0]=18'd123;expected[37:36]=3;
 raw=expected;cmd=1;tick(1);cmd=0;
 wait(av);@(negedge ck);warm=0;abort=1;tick(15);
 check(av&&!gv&&!ad&&ge==1&&local_starts==0&&packets==0&&!cv,"hidden actual grant after abort cannot emit HC");
 drains=4'b1110;tick(12);check(allocbusy&&!cv,"missing KV drain keeps hidden allocation");
 drains=15;tick(18);check(!allocbusy&&!cv&&!allocfault&&local_starts==0&&packets==0,"undelivered identity canceled by actual terminal acknowledgment");
 warm=1;reset();local_starts=0;packets=0;credits=0;requests=0;req_last=0;
 expected=0;expected[38]=1;expected[35:18]=4321;expected[17:0]=22;
 sendhc(expected);tick(40);
 check(ge==2&&local_starts==1&&packets==7&&!allocfault&&!ff,"soft reset preserves sole allocator epoch sequence");
 abort=1;drains=15;tick(20);check(!allocbusy&&!allocfault,"delivered epoch2 genuinely fault retired before next test");
 reset();local_starts=0;packets=0;credits=0;requests=0;req_last=0;
 expected=0;expected[38]=1;expected[35:18]=1200;expected[17:0]=66;raw=expected;cmd=1;tick(1);cmd=0;
 wait(av);@(negedge ck);warm=0;rst=0;tick(10);rst=1;tick(18);
 check(allocbusy&&ge==3&&local_starts==0&&packets==0&&!cv,"real midgrant host reset preserves accepted allocated tuple and blocks replay");
 drains=15;tick(20);check(!allocbusy&&!cv&&!allocfault,"midgrant reset retires only genuine retained identity after actual drains");
 warm=1;reset();expected=0;expected[38]=1;expected[35:18]=1300;expected[17:0]=67;sendhc(expected);tick(40);
 check(ge==4&&local_starts==1&&packets==7&&!allocfault&&!ff,"fresh allocation after reset-drain cancel uses next retained epoch4");
 $display("PASS actual token allocator transport checks=%0d epoch0/1cancel/2 retained",checks);$finish;
 end
 initial begin tick(2000);$fatal(1,"timeout");end
endmodule
