`timescale 1ns/1ps
// KV-P3-RTL 10-23: peer receive of the START-only transport (HCW 39) vs the 182-bit REF (qkd_ts182_ref_mu, run.sh).
// Die 1 (STRAPPED) gets class-22 v1 command frames from die 0.  Frame 0: START-only hc -> both decode it, DUT.hc ==
// REF.hc[38:0], no fault.  Frame 1: PW/DW field (frame bit 48+100) set -> REF takes it (hc[100]), the START-only DUT
// fails closed (fault) instead of silently dropping the bits.
module tb_hc39_rsv;
 reg ck=0;always #0.5 ck=~ck;
 reg rst_n=0,por_n=0,rx_v=0;reg[511:0]rx_d=0;
 wire[181:0]r_hc;wire[38:0]d_hc;wire r_f,d_f;
 `define HC39_PORTS(HCV,F) (.ck(ck),.rst_n(rst_n),.die_id(3'd1),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(),\
  .tx_v(),.tx_d(),.tx_cr(1'b0),.local_tk(93'd0),.local_kst(10'd0),.local_boot(2'd0),.cmd_v(1'b0),.cmd_hc('0),.cmd_cr(),.hc(HCV),\
  .tk8(),.kst8(),.boot8(),.seen(),.fault(F),.startup_allowed(1'b0),.local_service_ready(1'b0),.local_service_epoch(16'd0),\
  .begin_v(1'b0),.begin_epoch(16'd0),.begin_cr(),.begin_available(),.service_begin_v(),.service_begin_epoch(),.pending_advertised(),\
  .pending_epoch(),.service_ready8(),.pending_ack8(),.service_epoch8(),.ingest_permission(),.por_n(por_n),.token_wrap_fence_valid(1'b0),\
  .token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.token_allocator_fault(1'b0),\
  .package_abort(1'b0),.abort_drained(4'd0),.token_request_valid(),.token_request_ready(1'b0),.token_request_token(),\
  .token_request_position(),.token_request_generation(),.token_grant_valid(1'b0),.token_grant_ready(),.token_grant_epoch(16'd0),\
  .token_grant_token(18'd0),.token_grant_position(18'd0),.token_grant_generation(2'd0),.token_grant_tag(59'd0),.allocated_valid(1'b0),\
  .allocated_delivered(1'b0),.allocated_epoch(16'd0),.allocated_token(18'd0),.allocated_position(18'd0),.allocated_generation(2'd0),\
  .token_epoch_valid(),.token_epoch(),.cancel_valid(),.cancel_tag(),.cancel_generation(),.cancel_done(),.cancel_fault(),\
  .cancel_drained(),.terminal_accepted(1'b0));
 qkd_ts182_ref_mu #(.STRAPPED(1),.MU(1)) u_ref `HC39_PORTS(r_hc,r_f)
 qkd_host_ctrl_token_service_packet_collected_mu #(.STRAPPED(1),.MU(1),.HCW(39)) u_dut `HC39_PORTS(d_hc,d_f)
 function [511:0] frame(input[15:0]seq,input[181:0]hc);
  frame=512'h0122|(512'd2<<24)|(512'(seq)<<32)|(512'(hc)<<48);
 endfunction
 reg[181:0]h0;integer fails=0,seen0=0;reg ph0=1;
 task send(input[511:0]f);begin @(negedge ck);rx_v=1;rx_d=f;@(negedge ck);rx_v=0;rx_d=0;end endtask
 always @(negedge ck)if(rst_n&&ph0&&r_hc[38])begin seen0=seen0+1;if(d_hc!==r_hc[38:0])begin fails=fails+1;$display("ERR hc dut=%h ref=%h",d_hc,r_hc);end end
 initial begin
  h0=0;h0[38]=1;h0[37:36]=2'd1;h0[35:18]=18'd1234;h0[17:0]=18'h2_0005;
  repeat(3)@(negedge ck);por_n=1;repeat(2)@(negedge ck);rst_n=1;repeat(6)@(negedge ck);
  send(frame(16'd0,h0));repeat(8)@(negedge ck);
  if(seen0==0||r_f||d_f)begin fails=fails+1;$display("ERR frame0 seen=%0d ref_fault=%b dut_fault=%b",seen0,r_f,d_f);end
  ph0=0;send(frame(16'd1,h0|(182'd1<<100)));repeat(8)@(negedge ck);
  if(r_f||!r_hc[100])begin fails=fails+1;$display("ERR frame1 REF should take PW/DW: fault=%b hc100=%b",r_f,r_hc[100]);end
  if(!d_f)begin fails=fails+1;$display("ERR frame1 START-only DUT did not fault on a set PW/DW field");end
  if(fails==0)$display("PASS HC39_RSV frame0 START decoded equal (%0d cycles), frame1 PW/DW set: REF takes it, HCW39 faults",seen0);
  else $display("FAIL HC39_RSV fails=%0d",fails);
  $finish;
 end
endmodule
