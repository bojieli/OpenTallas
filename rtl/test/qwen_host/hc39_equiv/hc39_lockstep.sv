`timescale 1ns/1ps
// KV-P3-RTL 10-23: lockstep equivalence of the START-only HC transport (qkd_host_ctrl_token_service_packet_collected_mu
// HCW 39) against the 182-bit original (REF = the same module at commit 27befae4f, renamed qkd_ts182_ref_mu by run.sh).
// Drop-in for the transport in tb_mu_peer_e2e (same ports, 182-bit cmd_hc / hc on the bench side).  Both instances get
// the SAME inputs every cycle; REF gets the bench's 182-bit cmd_hc, the DUT its START slice cmd_hc[38:0] (the bench
// stream is START-only: cmd_hc[181:39] must be 0 whenever cmd_v, checked).  Every output is compared at every negedge
// (outputs are registered on posedge): DUT == REF on all of them, hc as DUT.hc == REF.hc[38:0] and REF.hc[181:39] == 0.
// The bench's system is driven by the DUT outputs (so the e2e bench's own checks also judge the DUT).
module hc39_lockstep #(parameter integer DIE=0,MUT=0,STRAPPED=0,ENABLE_SERVICE=0,ENABLE_TOKEN=0)(
 input wire ck,rst_n,input wire[2:0]die_id,
 input wire rx_v,input wire[511:0]rx_d,output wire rx_cr,
 output wire tx_v,output wire[511:0]tx_d,input wire tx_cr,
 input wire[92:0] local_tk,input wire[9:0]local_kst,input wire[1:0]local_boot,
 input wire cmd_v,input wire[181:0]cmd_hc,output wire cmd_cr,
 output wire[181:0]hc,
 output wire[743:0]tk8,output wire[79:0]kst8,output wire[15:0]boot8,output wire[7:0]seen,
 output wire fault,
 input wire startup_allowed,input wire local_service_ready,input wire[15:0]local_service_epoch,
 input wire begin_v,input wire[15:0]begin_epoch,
 output wire begin_cr,begin_available,
 output wire service_begin_v,output wire[15:0]service_begin_epoch,
 output wire pending_advertised,output wire[15:0]pending_epoch,
 output wire[7:0]service_ready8,pending_ack8,
 output wire[127:0]service_epoch8,output wire ingest_permission,
 input wire por_n,token_wrap_fence_valid,token_wrap_drained,token_wrap_link_reset_seen,token_wrap_retraining_done,
 input wire token_allocator_fault,
 input wire package_abort,input wire[3:0]abort_drained,
 output wire token_request_valid,input wire token_request_ready,
 output wire[17:0]token_request_token,token_request_position,output wire[1:0]token_request_generation,
 input wire token_grant_valid,output wire token_grant_ready,
 input wire[15:0]token_grant_epoch,input wire[17:0]token_grant_token,token_grant_position,
 input wire[1:0]token_grant_generation,input wire[58:0]token_grant_tag,
 input wire allocated_valid,allocated_delivered,input wire[15:0]allocated_epoch,
 input wire[17:0]allocated_token,allocated_position,input wire[1:0]allocated_generation,
 output wire token_epoch_valid,output wire[15:0]token_epoch,
 output wire cancel_valid,output wire[58:0]cancel_tag,output wire[1:0]cancel_generation,
 output wire cancel_done,cancel_fault,output wire[3:0]cancel_drained,input wire terminal_accepted
);
 // ---- every output but hc, concatenated in port order (1670 bits)
 `define HC39_OUTS(p) {p``rx_cr,p``tx_v,p``tx_d,p``cmd_cr,p``tk8,p``kst8,p``boot8,p``seen,p``fault,p``begin_cr,p``begin_available,\
  p``service_begin_v,p``service_begin_epoch,p``pending_advertised,p``pending_epoch,p``service_ready8,p``pending_ack8,\
  p``service_epoch8,p``ingest_permission,p``token_request_valid,p``token_request_token,p``token_request_position,\
  p``token_request_generation,p``token_grant_ready,p``token_epoch_valid,p``token_epoch,p``cancel_valid,p``cancel_tag,\
  p``cancel_generation,p``cancel_done,p``cancel_fault,p``cancel_drained}
 wire r_rx_cr,r_tx_v,r_cmd_cr,r_fault,r_begin_cr,r_begin_available,r_service_begin_v,r_pending_advertised,r_ingest_permission;
 wire[511:0]r_tx_d;wire[181:0]r_hc;wire[743:0]r_tk8;wire[79:0]r_kst8;wire[15:0]r_boot8,r_service_begin_epoch,r_pending_epoch,r_token_epoch;
 wire[7:0]r_seen,r_service_ready8,r_pending_ack8;wire[127:0]r_service_epoch8;
 wire r_token_request_valid,r_token_grant_ready,r_token_epoch_valid,r_cancel_valid,r_cancel_done,r_cancel_fault;
 wire[17:0]r_token_request_token,r_token_request_position;wire[1:0]r_token_request_generation,r_cancel_generation;
 wire[58:0]r_cancel_tag;wire[3:0]r_cancel_drained;
 wire[38:0]d_hc;
 qkd_ts182_ref_mu #(.DIE(DIE),.MUT(MUT),.STRAPPED(STRAPPED),.ENABLE_SERVICE(ENABLE_SERVICE),.ENABLE_TOKEN(ENABLE_TOKEN),.MU(1)) u_ref(
  .ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(r_rx_cr),.tx_v(r_tx_v),.tx_d(r_tx_d),.tx_cr(tx_cr),
  .local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(r_cmd_cr),
  .hc(r_hc),.tk8(r_tk8),.kst8(r_kst8),.boot8(r_boot8),.seen(r_seen),.fault(r_fault),.startup_allowed(startup_allowed),
  .local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),
  .begin_cr(r_begin_cr),.begin_available(r_begin_available),.service_begin_v(r_service_begin_v),.service_begin_epoch(r_service_begin_epoch),
  .pending_advertised(r_pending_advertised),.pending_epoch(r_pending_epoch),.service_ready8(r_service_ready8),.pending_ack8(r_pending_ack8),
  .service_epoch8(r_service_epoch8),.ingest_permission(r_ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid),
  .token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),
  .token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained),
  .token_request_valid(r_token_request_valid),.token_request_ready(token_request_ready),.token_request_token(r_token_request_token),
  .token_request_position(r_token_request_position),.token_request_generation(r_token_request_generation),.token_grant_valid(token_grant_valid),
  .token_grant_ready(r_token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),
  .token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),
  .allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),
  .allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(r_token_epoch_valid),
  .token_epoch(r_token_epoch),.cancel_valid(r_cancel_valid),.cancel_tag(r_cancel_tag),.cancel_generation(r_cancel_generation),
  .cancel_done(r_cancel_done),.cancel_fault(r_cancel_fault),.cancel_drained(r_cancel_drained),.terminal_accepted(terminal_accepted));
 qkd_host_ctrl_token_service_packet_collected_mu #(.DIE(DIE),.MUT(MUT),.STRAPPED(STRAPPED),.ENABLE_SERVICE(ENABLE_SERVICE),.ENABLE_TOKEN(ENABLE_TOKEN),.MU(1),.HCW(39)) u_dut(
  .ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),
  .local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc[38:0]),.cmd_cr(cmd_cr),
  .hc(d_hc),.tk8(tk8),.kst8(kst8),.boot8(boot8),.seen(seen),.fault(fault),.startup_allowed(startup_allowed),
  .local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),
  .begin_cr(begin_cr),.begin_available(begin_available),.service_begin_v(service_begin_v),.service_begin_epoch(service_begin_epoch),
  .pending_advertised(pending_advertised),.pending_epoch(pending_epoch),.service_ready8(service_ready8),.pending_ack8(pending_ack8),
  .service_epoch8(service_epoch8),.ingest_permission(ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid),
  .token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),
  .token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained),
  .token_request_valid(token_request_valid),.token_request_ready(token_request_ready),.token_request_token(token_request_token),
  .token_request_position(token_request_position),.token_request_generation(token_request_generation),.token_grant_valid(token_grant_valid),
  .token_grant_ready(token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),
  .token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),
  .allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),
  .allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(token_epoch_valid),
  .token_epoch(token_epoch),.cancel_valid(cancel_valid),.cancel_tag(cancel_tag),.cancel_generation(cancel_generation),
  .cancel_done(cancel_done),.cancel_fault(cancel_fault),.cancel_drained(cancel_drained),.terminal_accepted(terminal_accepted));
 assign hc={r_hc[181:39],d_hc};
 wire[1669:0]o_ref=`HC39_OUTS(r_),o_dut=`HC39_OUTS();
 integer ncyc=0,nmis=0,nstart=0,nhc=0,ntx=0;
 always @(negedge ck)if(por_n)begin
  ncyc=ncyc+1;
  if(cmd_v&&cmd_hc[181:39]!=0)begin nmis=nmis+1;if(nmis<6)$display("HC39 die%0d: bench cmd_hc not START-only %h",die_id,cmd_hc);end
  if(cmd_v&&cmd_hc[38])nstart=nstart+1;
  if(d_hc!=0)nhc=nhc+1;
  if(tx_v)ntx=ntx+1;
  if(o_ref!==o_dut||d_hc!==r_hc[38:0]||r_hc[181:39]!==0)begin
   nmis=nmis+1;
   if(nmis<6)$display("HC39 MISMATCH die%0d t=%0t hc dut=%h ref=%h outs_xor=%h",die_id,$time,d_hc,r_hc,o_ref^o_dut);
  end
 end
 final $display("HC39_LOCKSTEP die=%0d cycles=%0d mismatches=%0d start_cmds=%0d hc_nonzero_cycles=%0d tx_frames=%0d",die_id,ncyc,nmis,nstart,nhc,ntx);
endmodule
