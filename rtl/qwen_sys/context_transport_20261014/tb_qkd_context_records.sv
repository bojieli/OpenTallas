`timescale 1ns/1ps
// Actual allocator -> HC22 local producer -> native endpoint -> typed record
// -> two real static SRAM/CRC links -> retained receiver. The program ledger
// write-event face and cohort/head execution remain explicit component bounds.
module tb_qkd_context_records;
 parameter integer MUT=0;
 reg ck=0;always #0.4165 ck=~ck;
 reg fault_inject=0;reg por=0,warm=1;reg rst=0,cmd=0,abort=0;wire rr,gv,av,ad,ack;reg[3:0]drains=0;
 reg[181:0]raw=0;wire[15:0]ge;wire[17:0]gt,gp;wire[1:0]gg;wire[58:0]tag;wire allocfault,allocbusy;
 wire tx,cr,req,gr,tev,cv,cd,cf,ff;wire[511:0]packet;wire[181:0]hc;
 wire[17:0]rt,rp;wire[1:0]rg,cgen;wire[15:0]epoch;wire[58:0]ctag;wire[3:0]cda;
 reg txcredit=0;integer local_starts=0,packets=0,requests=0,credits=0,checks=0;
 reg req_last=0;reg[181:0]expected;integer scenario=0;
 qkd_host_ctrl_token_service_packet #(.DIE(0),.ENABLE_TOKEN(1)) dut(
 .ck(ck),.rst_n(rst),.die_id(3'd0),.rx_v(1'b0),.rx_d(512'd0),.tx_v(tx),.tx_d(packet),.tx_cr(txcredit),
 .local_tk(93'd0),.local_kst(10'd0),.local_boot(2'd3),.cmd_v(cmd),.cmd_hc(raw),.cmd_cr(cr),.hc(hc),.fault(ff),
 .startup_allowed(1'b1),.local_service_ready(1'b1),.local_service_epoch(16'd0),.begin_v(1'b0),.begin_epoch(16'd0),
 .por_n(por),.token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.token_allocator_fault(allocfault),.package_abort(abort),.abort_drained({(drains[3]&&!dut.busy&&dut.cn==0&&!dut.cv&&!tx&&!txcredit),drains[2:0]}),.token_request_valid(req),.token_request_ready(rr),
 .token_request_token(rt),.token_request_position(rp),.token_request_generation(rg),
 .token_grant_valid(gv),.token_grant_ready(gr),.token_grant_epoch(ge),.token_grant_token(gt),
 .token_grant_position(gp),.token_grant_generation(gg),.token_grant_tag(tag),
 .allocated_valid(av),.allocated_delivered(ad),.allocated_epoch(ge),.allocated_token(gt),.allocated_position(gp),.allocated_generation(gg),
 .token_epoch_valid(tev),.token_epoch(epoch),.cancel_valid(cv),.cancel_tag(ctag),.cancel_generation(cgen),
 .cancel_done(cd),.cancel_fault(cf),.cancel_drained(cda),.terminal_accepted(ack));
 ot_qwen_tp8_token_epoch_allocator allocator(.clk(ck),.por_n(por),.warm_ready(warm),
 .request_valid(req),.request_ready(rr),.request_token(fault_inject?18'd151936:rt),.request_position(rp),.request_generation(rg),
 .grant_valid(gv),.grant_ready(gr),.grant_epoch(ge),.grant_token(gt),.grant_position(gp),.grant_generation(gg),.grant_tag(tag),
 .allocated_valid(av),.allocated_delivered(ad),.terminal_valid(cv),.terminal_tag(ctag),.terminal_generation(cgen),
 .terminal_done(cd),.terminal_fault(cf),.terminal_kv_drained(cda[0]),.terminal_vm_drained(cda[1]),
 .terminal_collective_drained(cda[2]),.terminal_host_drained(cda[3]),
 .wrap_fence_valid(1'b0),.wrap_links_drained(1'b0),.wrap_link_reset_seen(1'b0),.wrap_retraining_done(1'b0),
 .busy(allocbusy),.identity_fault(allocfault),.terminal_accepted(ack));

 wire nr;wire[58:0]ntag;wire[1:0]ngen;wire[17:0]ntok,npos;wire ep_fault;
 qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))ne(
 .ck(ck),.por_n(por),.rst_n(rst),.hc(hc),.legacy_tk(93'd0),.image_ready(image_ready),.shared_epoch_valid(tev),.shared_epoch(epoch),
 .request_v(nr),.request_tag(ntag),.request_gen(ngen),.request_token(ntok),.request_pos(npos),.request_cr(1'b0),
 .result_v(1'b0),.result_tag(59'd0),.result_gen(2'd0),.result_done(1'b0),.result_fault(1'b0),.result_cause(4'd0),.result_token(18'd0),.result_value(32'd0),.result_cycles(32'd0),
 .kv_drained(1'b1),.vm_drained(1'b1),.collective_drained(1'b1),.host_drained(1'b1),.collective_busy(1'b0),.kv_flush(1'b0),
 .recovery_clear(1'b0),.cancel_release_v(1'b0),.cancel_release_tag(59'd0),.cancel_release_gen(2'd0),.protocol_fault(ep_fault));
 reg begin_v=0,auth_v=0,pwv=0,dwv=0;reg[9:0]pwa=0;reg[2:0]dwa=0;reg[63:0]pwd=0,dwd=0;
 reg[63:0]digest=64'h51484f5354505247;wire image_ready,cap,commit,ledger_fault;wire[15:0]image_epoch;wire[63:0]image_digest;
 localparam[63:0]FOOTER={32'h58504631,19'd0,1'b0,6'd37,4'd1,2'd2};
 qkd_program_commit ledger(.ck(ck),.rst_n(rst),.execution_active(1'b0),.control_stores_ready(1'b1),.begin_v(begin_v),.begin_epoch(16'h1234),.expected_pw(11'd1024),.expected_dw(4'd8),.auth_v(auth_v),.auth_epoch(16'h1234),.auth_digest(digest),.pw_v(pwv),.pw_addr(pwa),.pw_data(pwd),.pw_full_word(1'b1),.dw_v(dwv),.dw_addr(dwa),.dw_data(dwd),.dw_full_word(1'b1),.commit_v(commit),.ready(image_ready),.fault(ledger_fault),.installed_fusedcap(cap),.commit_epoch(image_epoch),.commit_digest(image_digest));
 reg send_slot=0;wire tv,ov,tx_fault;wire[547:0]record;
 qkd_host_native_context_tx u_ctx_tx(.ck(ck),.rst_n(rst),.send_slot(send_slot),.request_v(nr),.request_tag(ntag),.request_gen(ngen),.request_token(ntok),.request_position(npos),.token_epoch_valid(tev),.token_epoch(epoch),.program_ready(image_ready),.installed_fusedcap(cap),.program_epoch(image_epoch),.program_digest(image_digest),.tx_v(tv),.tx_observed_v(ov),.tx_record(record),.fault(tx_fault));
 reg le=0,read_slot=0,expect_slot=0,decode_slot=0;wire atv,brv,aa,ba;wire[582:0]atf;wire[547:0]brf;wire[7:0]ac,bc;
 reg[4:0]vp=0;reg[2914:0]fp=0;
 always @(posedge ck)if(!rst)begin vp<=0;fp<=0;end else begin vp<={vp,atv};fp<={fp,atf};end
 ot_qwen_static_slot_link #(.FW(548),.CW(16))a(.ck({5{ck}}),.rst_n(rst),.epoch_begin(le),.epoch(8'h29),.wr_v(tv),.wr_observed_v(ov),.wr_slot(6'd0),.wr_flit(record),.rd_v(read_slot),.rd_slot(6'd0),.rx_expect_v(1'b0),.rx_expect_slot(6'd0),.p_tx_up(1'b1),.p_rx_v(1'b0),.p_rx_flit(583'd0),.p_tx_v(atv),.p_tx_flit(atf),.epoch_abort(aa),.fault_cause(ac));
 ot_qwen_static_slot_link #(.FW(548),.CW(16))b(.ck({5{ck}}),.rst_n(rst),.epoch_begin(le),.epoch(8'h29),.wr_v(1'b0),.wr_observed_v(1'b0),.wr_slot(6'd0),.wr_flit(548'd0),.rd_v(1'b0),.rd_slot(6'd0),.rx_expect_v(expect_slot),.rx_expect_slot(6'd0),.p_tx_up(1'b1),.p_rx_v(vp[4]),.p_rx_flit(fp[2914-:583]),.rx_v(brv),.rx_flit(brf),.epoch_abort(ba),.fault_cause(bc));
 wire valid,rx_fault;wire[15:0]he,ie;wire[58:0]ht;wire[1:0]hg;wire hcapa;wire[63:0]id;
 wire[547:0]rx_mut=brf^(MUT==1?548'(1)<<78:MUT==2?548'(1)<<61:MUT==3?548'(1)<<43:548'd0);
 qfd_host_native_context_rx rx(.ck(ck),.rst_n(rst),.receive_slot(decode_slot),.rx_v(brv),.rx_record(rx_mut),.program_begin_v(1'b0),.program_ready(image_ready),.installed_fusedcap(cap),.program_epoch(image_epoch),.program_digest(image_digest),.head_context_v(1'b0),.head_stage(6'd37),.head_token(18'd140123),.head_position(18'd8191),.native_active(1'b0),.host_epoch_valid(valid),.host_epoch(he),.host_tag(ht),.host_gen(hg),.host_fusedcap(hcapa),.host_image_epoch(ie),.host_image_digest(id),.fault(rx_fault));
 always @(negedge ck)txcredit<=tx;
 task tick(input integer n);repeat(n)@(negedge ck);endtask
 integer i;
 initial begin
  tick(5);por=1;rst=1;tick(5);
  for(i=0;i<1024;i=i+1)begin pwd=i==1023?FOOTER:64'(i*17+3);digest={digest[56:0],digest[63:57]}^pwd^64'(i);end
  for(i=0;i<8;i=i+1)digest={digest[56:0],digest[63:57]}^64'(i+7)^64'(1024+i);
  begin_v=1;le=1;tick(1);begin_v=0;le=0;auth_v=1;tick(1);auth_v=0;tick(1);
  // Ledger boundary events use the exact authorized ascending digest schema.
  for(i=0;i<1024;i=i+1)begin pwv=1;pwa=i;pwd=i==1023?FOOTER:64'(i*17+3);tick(1);end
  pwv=0;for(i=0;i<8;i=i+1)begin dwv=1;dwa=i;dwd=i+7;tick(1);end
  dwv=0;tick(8);
  if(!image_ready||cap||ledger_fault)$fatal(1,"genuine ledger fixture did not commit actual1032-event image");
  raw=0;raw[38]=1;raw[35:18]=140123;raw[17:0]=8191;raw[37:36]=2;cmd=1;tick(1);cmd=0;tick(45);
  if(ep_fault||ff||allocfault||!ntag||ntok!=140123||npos!=8191)$fatal(1,"actual HOST source identity failed tev%0b ep%0b ctrl%0b alloc%0b tag%h token%0d pos%0d hc%h",tev,ep_fault,ff,allocfault,ntag,ntok,npos,hc);
  send_slot=1;tick(1);send_slot=0;tick(8);
  read_slot=1;tick(1);read_slot=0;tick(8);expect_slot=1;tick(1);expect_slot=0;tick(1);decode_slot=1;tick(1);decode_slot=0;tick(3);
  if(aa||ba||tx_fault||rx_fault||!valid||ht!==ntag||hg!==ngen||he!==epoch||hcapa!==cap||ie!==image_epoch||id!==image_digest)$fatal(1,"source/record/static SRAM link/retained context mismatch %h %h %b %b",ac,bc,rx_fault,valid);
  $display("PASS actual allocator/HC22/native endpoint -> kind12 -> SRAM/CRC TX3 PHY5 RX1 -> retained context; image ledger boundary explicit");$finish;
 end
 initial begin tick(2000);$fatal(1,"timeout");end
endmodule
