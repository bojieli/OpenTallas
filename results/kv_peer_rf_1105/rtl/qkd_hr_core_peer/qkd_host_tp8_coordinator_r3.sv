`timescale 1ns/1ps
// DIE-KV-70 11-04 RE-FORM of qkd_host_tp8_coordinator_mu (MU 1 body; same ports).
//  engine_result_* faces: one input stage (+1 edge).  result_cr still allows one outstanding result.
//  token_request_*: registered face, half rate, valid/ready safe (+1 edge; the request waits there while admission is closed).
//  program_consensus and the stable part of warm_ready: registered (+1 edge).  codec fault still drops warm_ready at once.
module qkd_host_tp8_coordinator_r3 #(parameter integer MU=1,parameter integer POST_UID_SLOT=0)(
 input wire ck_codec,ck_lifecycle,ck_post,por_n,
 input wire[7:0]peer_rx_valid,input wire[4095:0]peer_rx_data,output wire[7:0]peer_rx_ready,
 output wire[7:0]peer_tx_valid,output wire[4095:0]peer_tx_data,input wire[7:0]peer_tx_ready,
 input wire token_request_valid,input wire[17:0]token_request_token,token_request_position,input wire[1:0]token_request_gen,output wire token_request_ready,
 output wire token_grant_valid,input wire token_grant_ready,output wire[15:0]token_grant_epoch,output wire[17:0]token_grant_token,token_grant_position,output wire[1:0]token_grant_gen,output wire[58:0]token_grant_tag,
 output wire allocated_valid,allocated_delivered,
 input wire engine_admit_ready,output wire dispatch_valid,dispatched,output wire[58:0]cohort_tag,output wire[1:0]cohort_gen,
 output wire[7:0]accepted_ranks,output wire[255:0]participant_trace,output wire[143:0]participant_token,participant_pos,
 input wire engine_result_v,input wire[58:0]engine_result_tag,input wire[1:0]engine_result_gen,input wire engine_result_done,engine_result_fault,
 input wire[3:0]engine_result_cause,input wire[17:0]engine_result_token,input wire[31:0]engine_result_value,engine_result_cycles,output wire engine_result_cr,
 output wire program_consensus,output wire[15:0]program_epoch,output wire[63:0]program_digest,
 output wire[7:0]certificate_valid,output wire[527:0]certificate,output wire[255:0]certificate_prefix,
 output wire wrap_locked,identity_fault,recovery_complete,post_pending,output wire fault);
 wire[7:0] participant_valid,participant_accepted,cancel_valid,cancel_done,cancel_fault,cancel_accepted;
 wire[471:0] participant_tag,cancel_tag;
 wire[15:0] participant_gen,cancel_gen;
 wire[7:0] service_ready,native_ready,kv_drained,vm_drained,collective_drained,host_drained,context_owned,links_drained,link_reset_seen,retrained,program_ready;
 wire[127:0] service_epochs,certificate_epochs;
 wire[127:0] epochs;
 wire[511:0] digests;
 wire[7:0] terminal_released;
 wire codec_fault,post_fault,lifecycle_fault,result_transport_idle;
 wire step_issue_v,step_retire_v,step_retire_cq,cq_commit_v;
 wire[15:0] step_client_tag,step_retire_client_tag,cq_client_tag;
 wire[7:0] step_slot,step_retire_slot,cq_slot;
 wire[17:0] step_pos,step_retire_pos,step_retire_token,cq_pos,cq_token;
 wire terminal_accepted,post_retired,link_reset_request,retraining_request;
 wire[58:0] post_tag,acknowledged_tag;
 wire[1:0] post_gen,acknowledged_gen;
 wire[7:0] same_program,current_certificate;
 wire local_request_ready;
 wire request_admission;
 reg warm_q,consensus_q;
 reg recovery_active,recovery_required;
 reg recovery_start;
 // engine result face stage
 reg rs_v,rs_done,rs_fault;reg[58:0]rs_tag;reg[1:0]rs_gen;reg[3:0]rs_cause;reg[17:0]rs_token;reg[31:0]rs_value,rs_cycles;
 always @(posedge ck_codec)begin rs_tag<=engine_result_tag;rs_gen<=engine_result_gen;rs_done<=engine_result_done;rs_fault<=engine_result_fault;rs_cause<=engine_result_cause;rs_token<=engine_result_token;rs_value<=engine_result_value;rs_cycles<=engine_result_cycles;end
 always @(posedge ck_codec or negedge por_n)if(!por_n)rs_v<=0;else rs_v<=engine_result_v;
 assign program_epoch=epochs[15:0];assign program_digest=digests[63:0];
 for(genvar i=0;i<8;i=i+1)begin:g_program
  assign current_certificate[i]=certificate_valid[i]&&certificate_epochs[i*16+:16]==service_epochs[i*16+:16];
  assign same_program[i]=epochs[i*16+:16]==epochs[15:0]&&digests[i*64+:64]==digests[63:0];
 end
 wire consensus_now=(&program_ready)&&(&same_program);
 assign program_consensus=consensus_q;
 assign fault=codec_fault||post_fault||identity_fault||lifecycle_fault;
 assign request_admission=!wrap_locked&&!recovery_active&&!recovery_required&&!identity_fault;
 // token request face stage
 reg rq_v,rq_rdy;reg[17:0]rq_tok,rq_pos;reg[1:0]rq_gen;
 assign token_request_ready=rq_rdy;
 wire rq_take=token_request_valid&&rq_rdy;
 wire rq_fire=rq_v&&request_admission&&local_request_ready;
 always @(posedge ck_lifecycle)if(rq_take)begin rq_tok<=token_request_token;rq_pos<=token_request_position;rq_gen<=token_request_gen;end
 always @(posedge ck_lifecycle or negedge por_n)if(!por_n)begin rq_v<=0;rq_rdy<=0;end else begin
  if(rq_take)rq_v<=1;else if(rq_fire)rq_v<=0;
  rq_rdy<=(!rq_v||rq_fire)&&!rq_take;
 end
 reg warm_ready; // DIE-KV-73 r4: registered, warm rise and codec fault reach the lifecycle +1 edge
 always @(posedge ck_lifecycle or negedge por_n)begin
  if(!por_n)begin recovery_active<=0;recovery_required<=0;recovery_start<=0;warm_q<=0;consensus_q<=0;warm_ready<=0;end
  else begin
   consensus_q<=consensus_now;
   warm_q<=(&service_ready)&&(&current_certificate)&&consensus_now;
   warm_ready<=warm_q&&!codec_fault;
   recovery_start<=0;
   if((rs_v&&rs_fault)||(|(cancel_valid&cancel_fault)))recovery_required<=1;
   if(!recovery_active&&(wrap_locked||identity_fault||recovery_required)&&!allocated_valid&&!post_pending&&result_transport_idle&&
      (&kv_drained)&&(&vm_drained)&&(&collective_drained)&&(&host_drained))begin recovery_active<=1;recovery_start<=1;end
   if(recovery_complete)begin recovery_active<=0;recovery_required<=0;end
  end
 end
 qkd_host_peer_coordinator_codec_r3 #(.MU(1)) u_peer(
 .ck(ck_codec),.por_n(por_n),.rx_valid(peer_rx_valid),.rx_data(peer_rx_data),.rx_ready(peer_rx_ready),.tx_valid(peer_tx_valid),.tx_data(peer_tx_data),.tx_ready(peer_tx_ready),
 .allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),.allocated_tag(token_grant_tag),.allocated_gen(token_grant_gen),.allocated_position(token_grant_position),
 .participant_valid(participant_valid),.participant_tag(participant_tag),.participant_gen(participant_gen),.participant_trace(participant_trace),.participant_token(participant_token),.participant_pos(participant_pos),.participant_accepted(participant_accepted),
 .cancel_valid(cancel_valid),.cancel_done(cancel_done),.cancel_fault(cancel_fault),.cancel_tag(cancel_tag),.cancel_gen(cancel_gen),.cancel_accepted(cancel_accepted),
 .service_ready(service_ready),.native_ready(native_ready),.kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),.host_drained(host_drained),.context_owned(context_owned),.links_drained(links_drained),.link_reset_seen(link_reset_seen),.retrained(retrained),
 .service_epoch(service_epochs),.certificate_epoch(certificate_epochs),.program_ready(program_ready),.program_epoch(epochs),.program_digest(digests),
 .result_v(rs_v),.result_tag(rs_tag),.result_gen(rs_gen),.result_done(rs_done),.result_fault(rs_fault),.result_cause(rs_cause),.result_token(rs_token),.result_value(rs_value),.result_cycles(rs_cycles),.result_cr(engine_result_cr),
 .terminal_accepted(terminal_accepted),.terminal_tag(acknowledged_tag),.terminal_gen(acknowledged_gen),.post_retired(post_retired),.terminal_released(terminal_released),.result_transport_idle(result_transport_idle),.link_reset_request(link_reset_request),.retraining_request(retraining_request),
 .step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
 .cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.certificate_valid(certificate_valid),.certificate(certificate),.certificate_prefix(certificate_prefix),.fault(codec_fault));
 qkd_host_coordinator_services_r3 #(.MU(1),.POST_UID_SLOT(POST_UID_SLOT)) u_lifecycle(
 .clk(ck_lifecycle),.ck_post(ck_post),.por_n(por_n),.warm_ready(warm_ready),
 .request_valid(rq_v&&request_admission),.request_ready(local_request_ready),.request_token(rq_tok),.request_position(rq_pos),.request_generation(rq_gen),
 .grant_valid(token_grant_valid),.grant_ready(token_grant_ready),.grant_epoch(token_grant_epoch),.grant_token(token_grant_token),.grant_position(token_grant_position),.grant_generation(token_grant_gen),.grant_tag(token_grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),
 .participant_valid(participant_valid),.participant_tag(participant_tag),.participant_generation(participant_gen),.participant_accepted(participant_accepted),.engine_admit_ready(engine_admit_ready),.participant_ready(native_ready),.dispatch_valid(dispatch_valid),.dispatched(dispatched),.cohort_tag(cohort_tag),.cohort_generation(cohort_gen),.accepted_ranks(accepted_ranks),
 .result_valid(rs_v),.result_done(rs_done),.result_fault(rs_fault),.result_tag(rs_tag),.result_generation(rs_gen),
 .cancel_valid(cancel_valid),.cancel_done(cancel_done),.cancel_fault(cancel_fault),.cancel_tag(cancel_tag),.cancel_generation(cancel_gen),.cancel_accepted(cancel_accepted),
 .kv_drained(kv_drained),.vm_drained(vm_drained),.collective_drained(collective_drained),.host_drained(host_drained),
 .post_retired(post_retired),.post_tag(post_tag),.post_generation(post_gen),.post_pending(post_pending),.acknowledged_tag(acknowledged_tag),.acknowledged_generation(acknowledged_gen),
 .recovery_start(recovery_start),.links_drained(links_drained),.link_reset_seen(link_reset_seen),.retraining_done(retrained),.link_reset_request(link_reset_request),.retraining_request(retraining_request),.recovery_complete(recovery_complete),.wrap_locked(wrap_locked),.identity_fault(identity_fault),.terminal_accepted(terminal_accepted),.lifecycle_fault(lifecycle_fault),
 .step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
 .cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cancel_released(terminal_released),.cancel_release_required(8'hff),.result_transport_idle(result_transport_idle),.host_observer_fault(codec_fault),.post_fault(post_fault));
endmodule
