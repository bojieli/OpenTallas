`timescale 1ns/1ps
module tb;
parameter integer SEED=1, N=200000;
reg ck=0; always #1 ck=~ck;

reg  rst_n;
reg [2:0] die_id;
reg  rx_v;
reg [511:0] rx_d;
reg  tx_cr;
reg [92:0] local_tk;
reg [9:0] local_kst;
reg [1:0] local_boot;
reg  cmd_v;
reg [38:0] cmd_hc;
reg  startup_allowed;
reg  local_service_ready;
reg [15:0] local_service_epoch;
reg  begin_v;
reg [15:0] begin_epoch;
reg  por_n;
reg  token_wrap_fence_valid;
reg  token_wrap_drained;
reg  token_wrap_link_reset_seen;
reg  token_wrap_retraining_done;
reg  token_allocator_fault;
reg  package_abort;
reg [3:0] abort_drained;
reg  token_request_ready;
reg  token_grant_valid;
reg [15:0] token_grant_epoch;
reg [17:0] token_grant_token;
reg [17:0] token_grant_position;
reg [1:0] token_grant_generation;
reg [58:0] token_grant_tag;
reg  allocated_valid;
reg  allocated_delivered;
reg [15:0] allocated_epoch;
reg [17:0] allocated_token;
reg [17:0] allocated_position;
reg [1:0] allocated_generation;
reg  terminal_accepted;
wire  r_rx_cr, d_rx_cr;
wire  r_tx_v, d_tx_v;
wire [511:0] r_tx_d, d_tx_d;
wire  r_cmd_cr, d_cmd_cr;
wire [38:0] r_hc, d_hc;
wire [743:0] r_tk8, d_tk8;
wire [79:0] r_kst8, d_kst8;
wire [15:0] r_boot8, d_boot8;
wire [7:0] r_seen, d_seen;
wire  r_fault, d_fault;
wire  r_begin_cr, d_begin_cr;
wire  r_begin_available, d_begin_available;
wire  r_service_begin_v, d_service_begin_v;
wire [15:0] r_service_begin_epoch, d_service_begin_epoch;
wire  r_pending_advertised, d_pending_advertised;
wire [15:0] r_pending_epoch, d_pending_epoch;
wire [7:0] r_service_ready8, d_service_ready8;
wire [7:0] r_pending_ack8, d_pending_ack8;
wire [127:0] r_service_epoch8, d_service_epoch8;
wire  r_ingest_permission, d_ingest_permission;
wire  r_token_request_valid, d_token_request_valid;
wire [17:0] r_token_request_token, d_token_request_token;
wire [17:0] r_token_request_position, d_token_request_position;
wire [1:0] r_token_request_generation, d_token_request_generation;
wire  r_token_grant_ready, d_token_grant_ready;
wire  r_token_epoch_valid, d_token_epoch_valid;
wire [15:0] r_token_epoch, d_token_epoch;
wire  r_cancel_valid, d_cancel_valid;
wire [58:0] r_cancel_tag, d_cancel_tag;
wire [1:0] r_cancel_generation, d_cancel_generation;
wire  r_cancel_done, d_cancel_done;
wire  r_cancel_fault, d_cancel_fault;
wire [3:0] r_cancel_drained, d_cancel_drained;
qkd_host_ctrl_token_service_packet_collected_mu_ref #(.DIE(0),.MUT(0),.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1),.HCW(39),.CONST_LANE_WRITES(0)) u_r(.ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(r_rx_cr),.tx_v(r_tx_v),.tx_d(r_tx_d),.tx_cr(tx_cr),.local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(r_cmd_cr),.hc(r_hc),.tk8(r_tk8),.kst8(r_kst8),.boot8(r_boot8),.seen(r_seen),.fault(r_fault),.startup_allowed(startup_allowed),.local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),.begin_cr(r_begin_cr),.begin_available(r_begin_available),.service_begin_v(r_service_begin_v),.service_begin_epoch(r_service_begin_epoch),.pending_advertised(r_pending_advertised),.pending_epoch(r_pending_epoch),.service_ready8(r_service_ready8),.pending_ack8(r_pending_ack8),.service_epoch8(r_service_epoch8),.ingest_permission(r_ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid),.token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),.token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained),.token_request_valid(r_token_request_valid),.token_request_ready(token_request_ready),.token_request_token(r_token_request_token),.token_request_position(r_token_request_position),.token_request_generation(r_token_request_generation),.token_grant_valid(token_grant_valid),.token_grant_ready(r_token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),.token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),.allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(r_token_epoch_valid),.token_epoch(r_token_epoch),.cancel_valid(r_cancel_valid),.cancel_tag(r_cancel_tag),.cancel_generation(r_cancel_generation),.cancel_done(r_cancel_done),.cancel_fault(r_cancel_fault),.cancel_drained(r_cancel_drained),.terminal_accepted(terminal_accepted));
qkd_host_ctrl_token_service_packet_collected_mu #(.DIE(0),.MUT(0),.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1),.HCW(39),.CONST_LANE_WRITES(1),.HDR_PREDECODE(HP)) u_d(.ck(ck),.rst_n(rst_n),.die_id(die_id),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(d_rx_cr),.tx_v(d_tx_v),.tx_d(d_tx_d),.tx_cr(tx_cr),.local_tk(local_tk),.local_kst(local_kst),.local_boot(local_boot),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.cmd_cr(d_cmd_cr),.hc(d_hc),.tk8(d_tk8),.kst8(d_kst8),.boot8(d_boot8),.seen(d_seen),.fault(d_fault),.startup_allowed(startup_allowed),.local_service_ready(local_service_ready),.local_service_epoch(local_service_epoch),.begin_v(begin_v),.begin_epoch(begin_epoch),.begin_cr(d_begin_cr),.begin_available(d_begin_available),.service_begin_v(d_service_begin_v),.service_begin_epoch(d_service_begin_epoch),.pending_advertised(d_pending_advertised),.pending_epoch(d_pending_epoch),.service_ready8(d_service_ready8),.pending_ack8(d_pending_ack8),.service_epoch8(d_service_epoch8),.ingest_permission(d_ingest_permission),.por_n(por_n),.token_wrap_fence_valid(token_wrap_fence_valid),.token_wrap_drained(token_wrap_drained),.token_wrap_link_reset_seen(token_wrap_link_reset_seen),.token_wrap_retraining_done(token_wrap_retraining_done),.token_allocator_fault(token_allocator_fault),.package_abort(package_abort),.abort_drained(abort_drained),.token_request_valid(d_token_request_valid),.token_request_ready(token_request_ready),.token_request_token(d_token_request_token),.token_request_position(d_token_request_position),.token_request_generation(d_token_request_generation),.token_grant_valid(token_grant_valid),.token_grant_ready(d_token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),.token_grant_position(token_grant_position),.token_grant_generation(token_grant_generation),.token_grant_tag(token_grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_epoch(allocated_epoch),.allocated_token(allocated_token),.allocated_position(allocated_position),.allocated_generation(allocated_generation),.token_epoch_valid(d_token_epoch_valid),.token_epoch(d_token_epoch),.cancel_valid(d_cancel_valid),.cancel_tag(d_cancel_tag),.cancel_generation(d_cancel_generation),.cancel_done(d_cancel_done),.cancel_fault(d_cancel_fault),.cancel_drained(d_cancel_drained),.terminal_accepted(terminal_accepted));
parameter integer HP=1;
integer sd; integer cyc, mism=0, nrxw=0, nfault=0, ntake=0, cut, b; reg [2:0] die; reg [511:0] f; reg [1:0] e;
function [511:0] frame(input integer dummy);
 reg [511:0] x; integer t,c,k;
 begin
  x={$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom,$urandom};
  t=$urandom%8; x[7:0]= t<3?8'h21: t<5?8'h22: t<7?8'h23: $urandom;
  c=$urandom%8; x[15:8]= c<3?8'd1: c<7?8'd2: $urandom;
  if($urandom%8) x[23:19]=0;
  x[18:16]= ($urandom%3==0)?3'd0:$urandom;
  x[31:24]= ($urandom%6)? (8'd1<<die) : (($urandom%2)?8'd1:$urandom);
  x[47:32]= $urandom%4;
  x[63:48]= $urandom%4; x[169:154]=$urandom%4; x[245:230]=$urandom%8; x[262:247]=$urandom%4;
  if($urandom%4) x[63:61]=0;
  if($urandom%4) x[231:230]=x[65:64];
  if($urandom%4) x[83:66]=$urandom%151936; else x[83:66]=151930+$urandom%12;
  k=$urandom%9; cut= k==0?64: k==1?65: k==2?87: k==3?153: k==4?170: k==5?230: k==6?263: k==7?512: 48+$urandom%464;
  for(b=0;b<512;b=b+1) if(b>=cut && !(b>=48 && b<87 && cut==87)) x[b]=0;
  if(cut==87 || cut==230 || cut==263) begin for(b=87;b<230;b=b+1) x[b]=0; end
  if($urandom%5==0) x[$urandom%512]=~x[$urandom%512];
  if($urandom%7==0) begin b=cut-1-($urandom%3); if(b>=24 && b<512) x[b]=1; end
  if($urandom%20<19) begin  // well-formed frame for the current role (expected sequence from the reference state)
   for(b=87;b<512;b=b+1) x[b]=0;
   x[23:19]=0; x[31:24]=8'd1<<die;
   if(die==0) begin x[7:0]=8'h21; x[15:8]=8'd2; x[18:16]=1+$urandom%7; x[169:154]=u_r.g_mu.epoch; x[153]=$urandom; for(b=87;b<154;b=b+1) x[b]=$urandom; end
   else begin x[18:16]=0; x[86]=0;
    if($urandom%3==0) begin x[7:0]=8'h22; x[15:8]=8'd1; end
    else if($urandom%2) begin x[7:0]=8'h22; x[15:8]=8'd2; x[86]=1; x[246]=1; x[65:64]=$urandom; x[231:230]=x[65:64]; x[83:66]=$urandom%151936;
      x[245:232]=$urandom; x[262:247]=u_r.g_mu.epoch; end
    else begin x[7:0]=8'h23; x[15:8]=8'd2; x[64]=$urandom%4==0; x[63:48]=u_r.g_mu.epoch+(x[64]?0:1); end end
   x[47:32]= u_r.g_mu.seq_seen[x[18:16]] ? u_r.g_mu.seq_rx[x[18:16]*16+:16]+16'd1+u_r.g_mu.count : 16'd0;
   if($urandom%20==0) x[$urandom%512]=1;
   if($urandom%10==0) begin k=$urandom%7; x[k==0?64:k==1?65:k==2?87:k==3?153:k==4?170:k==5?230:263]=1; end
  end
  frame=x;
 end
endfunction
initial begin
 rst_n=0; por_n=0; die=0; die_id=0; rx_v=0; rx_d=0; tx_cr=0; local_tk=0; local_kst=0; local_boot=0; cmd_v=0; cmd_hc=0;
 startup_allowed=0; local_service_ready=0; local_service_epoch=0; begin_v=0; begin_epoch=0; token_wrap_fence_valid=0; token_wrap_drained=0;
 token_wrap_link_reset_seen=0; token_wrap_retraining_done=0; token_allocator_fault=0; package_abort=0; abort_drained=0; token_request_ready=0;
 token_grant_valid=0; token_grant_epoch=0; token_grant_token=0; token_grant_position=0; token_grant_generation=0; token_grant_tag=0;
 allocated_valid=0; allocated_delivered=0; allocated_epoch=0; allocated_token=0; allocated_position=0; allocated_generation=0; terminal_accepted=0;
 sd=SEED; e=$urandom(sd);
 for(cyc=0;cyc<N;cyc=cyc+1) begin
  @(negedge ck);
  if(cyc==3) por_n=1;
  if(cyc==4) rst_n=1;
  if(cyc>10 && $urandom%250==0) begin rst_n=0; if($urandom%2) begin die=($urandom%3==0)?$urandom:0; end end else if(!rst_n && $urandom%3==0 && cyc>4) rst_n=1;
  if(cyc>10 && $urandom%20000==0) por_n=0; else if(!por_n && cyc>4) por_n=1;
  if($urandom%9000==0) die=$urandom;
  die_id=die;
  rx_v=($urandom%3==0) && u_r.g_mu.count+u_r.g_mu.rv<4; rx_d=frame(0);
  tx_cr=($urandom%4==0) && u_r.g_mu.credits<4;
  if($urandom%50==0) begin local_tk={$urandom,$urandom,$urandom}; local_kst=$urandom; local_boot=$urandom; end
  cmd_v=($urandom%25==0) && die==0 && u_r.g_mu.cn+u_r.g_mu.cv<4; cmd_hc={$urandom,$urandom}; if($urandom%3) cmd_hc[15:13]=0; cmd_hc[35:18]=$urandom%160000;
  if($urandom%200==0) startup_allowed=$urandom; if($urandom%40==0) local_service_ready=$urandom; if($urandom%60==0) local_service_epoch=$urandom%4;
  begin_v=($urandom%3000==0); begin_epoch=$urandom%5;
  token_wrap_fence_valid=($urandom%2000==0) || (r_fault && !u_r.g_mu.retained_request && !allocated_valid && !u_r.g_mu.allocated_vq && !r_cancel_valid && $urandom%40==0); token_wrap_drained=($urandom%64!=0); token_wrap_link_reset_seen=($urandom%64!=0); token_wrap_retraining_done=($urandom%64!=0);
  token_allocator_fault=($urandom%50000==0); package_abort=($urandom%1500==0); abort_drained=$urandom; token_request_ready=$urandom;
  token_grant_valid=($urandom%10==0); token_grant_epoch=$urandom%8; token_grant_token=$urandom; token_grant_position=$urandom%4; token_grant_generation=$urandom; token_grant_tag={$urandom,$urandom};
  allocated_valid=($urandom%32==0); allocated_delivered=($urandom%4==0); allocated_epoch=$urandom%8; allocated_token=$urandom; allocated_position=$urandom%4; allocated_generation=$urandom; terminal_accepted=$urandom;
  @(posedge ck); #0.5;
  if(u_r.g_mu.take) ntake=ntake+1;
  if(u_r.g_mu.take && u_r.g_mu.hdr && u_r.g_mu.sequence_ok && !u_r.fault) nrxw=nrxw+1;
  if(r_fault) nfault=nfault+1;
  if((r_rx_cr!==d_rx_cr) || (r_tx_v!==d_tx_v) || (r_tx_d!==d_tx_d) || (r_cmd_cr!==d_cmd_cr) || (r_hc!==d_hc) || (r_tk8!==d_tk8) || (r_kst8!==d_kst8) || (r_boot8!==d_boot8) || (r_seen!==d_seen) || (r_fault!==d_fault) || (r_begin_cr!==d_begin_cr) || (r_begin_available!==d_begin_available) || (r_service_begin_v!==d_service_begin_v) || (r_service_begin_epoch!==d_service_begin_epoch) || (r_pending_advertised!==d_pending_advertised) || (r_pending_epoch!==d_pending_epoch) || (r_service_ready8!==d_service_ready8) || (r_pending_ack8!==d_pending_ack8) || (r_service_epoch8!==d_service_epoch8) || (r_ingest_permission!==d_ingest_permission) || (r_token_request_valid!==d_token_request_valid) || (r_token_request_token!==d_token_request_token) || (r_token_request_position!==d_token_request_position) || (r_token_request_generation!==d_token_request_generation) || (r_token_grant_ready!==d_token_grant_ready) || (r_token_epoch_valid!==d_token_epoch_valid) || (r_token_epoch!==d_token_epoch) || (r_cancel_valid!==d_cancel_valid) || (r_cancel_tag!==d_cancel_tag) || (r_cancel_generation!==d_cancel_generation) || (r_cancel_done!==d_cancel_done) || (r_cancel_fault!==d_cancel_fault) || (r_cancel_drained!==d_cancel_drained)) begin
   mism=mism+1;
   if(mism<6) begin $display("MISMATCH cyc=%0d", cyc);

    if(r_rx_cr!==d_rx_cr) $display("  rx_cr ref=%h dut=%h", r_rx_cr, d_rx_cr);
    if(r_tx_v!==d_tx_v) $display("  tx_v ref=%h dut=%h", r_tx_v, d_tx_v);
    if(r_tx_d!==d_tx_d) $display("  tx_d ref=%h dut=%h", r_tx_d, d_tx_d);
    if(r_cmd_cr!==d_cmd_cr) $display("  cmd_cr ref=%h dut=%h", r_cmd_cr, d_cmd_cr);
    if(r_hc!==d_hc) $display("  hc ref=%h dut=%h", r_hc, d_hc);
    if(r_tk8!==d_tk8) $display("  tk8 ref=%h dut=%h", r_tk8, d_tk8);
    if(r_kst8!==d_kst8) $display("  kst8 ref=%h dut=%h", r_kst8, d_kst8);
    if(r_boot8!==d_boot8) $display("  boot8 ref=%h dut=%h", r_boot8, d_boot8);
    if(r_seen!==d_seen) $display("  seen ref=%h dut=%h", r_seen, d_seen);
    if(r_fault!==d_fault) $display("  fault ref=%h dut=%h", r_fault, d_fault);
    if(r_begin_cr!==d_begin_cr) $display("  begin_cr ref=%h dut=%h", r_begin_cr, d_begin_cr);
    if(r_begin_available!==d_begin_available) $display("  begin_available ref=%h dut=%h", r_begin_available, d_begin_available);
    if(r_service_begin_v!==d_service_begin_v) $display("  service_begin_v ref=%h dut=%h", r_service_begin_v, d_service_begin_v);
    if(r_service_begin_epoch!==d_service_begin_epoch) $display("  service_begin_epoch ref=%h dut=%h", r_service_begin_epoch, d_service_begin_epoch);
    if(r_pending_advertised!==d_pending_advertised) $display("  pending_advertised ref=%h dut=%h", r_pending_advertised, d_pending_advertised);
    if(r_pending_epoch!==d_pending_epoch) $display("  pending_epoch ref=%h dut=%h", r_pending_epoch, d_pending_epoch);
    if(r_service_ready8!==d_service_ready8) $display("  service_ready8 ref=%h dut=%h", r_service_ready8, d_service_ready8);
    if(r_pending_ack8!==d_pending_ack8) $display("  pending_ack8 ref=%h dut=%h", r_pending_ack8, d_pending_ack8);
    if(r_service_epoch8!==d_service_epoch8) $display("  service_epoch8 ref=%h dut=%h", r_service_epoch8, d_service_epoch8);
    if(r_ingest_permission!==d_ingest_permission) $display("  ingest_permission ref=%h dut=%h", r_ingest_permission, d_ingest_permission);
    if(r_token_request_valid!==d_token_request_valid) $display("  token_request_valid ref=%h dut=%h", r_token_request_valid, d_token_request_valid);
    if(r_token_request_token!==d_token_request_token) $display("  token_request_token ref=%h dut=%h", r_token_request_token, d_token_request_token);
    if(r_token_request_position!==d_token_request_position) $display("  token_request_position ref=%h dut=%h", r_token_request_position, d_token_request_position);
    if(r_token_request_generation!==d_token_request_generation) $display("  token_request_generation ref=%h dut=%h", r_token_request_generation, d_token_request_generation);
    if(r_token_grant_ready!==d_token_grant_ready) $display("  token_grant_ready ref=%h dut=%h", r_token_grant_ready, d_token_grant_ready);
    if(r_token_epoch_valid!==d_token_epoch_valid) $display("  token_epoch_valid ref=%h dut=%h", r_token_epoch_valid, d_token_epoch_valid);
    if(r_token_epoch!==d_token_epoch) $display("  token_epoch ref=%h dut=%h", r_token_epoch, d_token_epoch);
    if(r_cancel_valid!==d_cancel_valid) $display("  cancel_valid ref=%h dut=%h", r_cancel_valid, d_cancel_valid);
    if(r_cancel_tag!==d_cancel_tag) $display("  cancel_tag ref=%h dut=%h", r_cancel_tag, d_cancel_tag);
    if(r_cancel_generation!==d_cancel_generation) $display("  cancel_generation ref=%h dut=%h", r_cancel_generation, d_cancel_generation);
    if(r_cancel_done!==d_cancel_done) $display("  cancel_done ref=%h dut=%h", r_cancel_done, d_cancel_done);
    if(r_cancel_fault!==d_cancel_fault) $display("  cancel_fault ref=%h dut=%h", r_cancel_fault, d_cancel_fault);
    if(r_cancel_drained!==d_cancel_drained) $display("  cancel_drained ref=%h dut=%h", r_cancel_drained, d_cancel_drained);
   end
  end
 end
 if(mism==0) $display("PASS SEED=%0d HP=%0d cycles=%0d take=%0d rx_accept=%0d fault_cycles=%0d", SEED, HP, N, ntake, nrxw, nfault);
 else $display("FAIL SEED=%0d HP=%0d mismatching cycles=%0d take=%0d rx_accept=%0d", SEED, HP, mism, ntake, nrxw);
 $finish;
end
endmodule
