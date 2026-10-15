`timescale 1ns/1ps
// Protocol boundary test, not a native engine/HBM qualification. HC and the
// engine-result face are explicit external stimuli; request acceptance, result
// credit, terminal barrier and empty-context receipts are actual RTL outputs.
module tb_qkd_host_peer_lifecycle;
 reg ck=0;always #5 ck=~ck;reg por_n=0;
 wire[7:0]peer_rx_valid,peer_rx_ready,peer_tx_valid,peer_tx_ready;
 wire[4095:0]peer_rx_data,peer_tx_data;
 reg token_request_valid=0;reg[17:0]token_request_token=100,token_request_position=0;reg[1:0]token_request_gen=1;wire token_request_ready;
 wire token_grant_valid;reg token_grant_ready=0;wire[15:0]token_grant_epoch;wire[17:0]token_grant_token,token_grant_position;wire[1:0]token_grant_gen;wire[58:0]token_grant_tag;wire allocated_valid,allocated_delivered;
 wire dispatch_valid,dispatched;wire[58:0]cohort_tag;wire[1:0]cohort_gen;wire[7:0]accepted_ranks;
 reg engine_result_v=0;reg[58:0]engine_result_tag=0;reg[1:0]engine_result_gen=0;reg engine_result_done=0,engine_result_fault=0;
 reg[3:0]engine_result_cause=0;reg[17:0]engine_result_token=321;reg[31:0]engine_result_value=32'habc123,engine_result_cycles=42;wire engine_result_cr;
 wire program_consensus,wrap_locked,identity_fault,recovery_complete,post_pending,fault;
 wire[15:0]program_epoch;wire[63:0]program_digest;
 wire[7:0]codec_fault,endpoint_fault,result_credit,context_owned,cancel_released;
 wire[7:0]request_v,request_cr,result_v,result_done,result_fault;
 wire[471:0]request_tag,result_tag;wire[15:0]request_gen,result_gen;wire[255:0]request_trace,result_value,result_cycles;
 wire[143:0]request_token,request_pos,result_token;wire[31:0]result_cause;
 wire[7:0]release_v;wire[471:0]release_tag;wire[15:0]release_gen;
 wire[743:0]tk;
 reg[7:0]hc_mask=255,cancel_offer=0;wire[7:0]cancel_ack;integer release_count=0;
 reg[181:0]hc=0;reg shared_epoch_valid=0;reg[15:0]shared_epoch=0;
 reg step_issue_v=0,step_retire_v=0,step_retire_cq=0,cq_commit_v=0,certificate_v=0;
 reg[17:0]pos=0;reg[7:0]drains=255;
 wire[7:0]reset_request,retrain_request,recovery_clear;
 qkd_host_tp8_coordinator d(.ck_codec(ck),.ck_lifecycle(ck),.ck_post(ck),.por_n(por_n),.peer_rx_valid(peer_rx_valid),.peer_rx_data(peer_rx_data),.peer_rx_ready(peer_rx_ready),.peer_tx_valid(peer_tx_valid),.peer_tx_data(peer_tx_data),.peer_tx_ready(peer_tx_ready),
 .token_request_valid(token_request_valid),.token_request_token(token_request_token),.token_request_position(token_request_position),.token_request_gen(token_request_gen),.token_request_ready(token_request_ready),.token_grant_valid(token_grant_valid),.token_grant_ready(token_grant_ready),.token_grant_epoch(token_grant_epoch),.token_grant_token(token_grant_token),.token_grant_position(token_grant_position),.token_grant_gen(token_grant_gen),.token_grant_tag(token_grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),
 .engine_admit_ready(1'b1),.dispatch_valid(dispatch_valid),.dispatched(dispatched),.cohort_tag(cohort_tag),.cohort_gen(cohort_gen),.accepted_ranks(accepted_ranks),.participant_trace(),.participant_token(),.participant_pos(),
 .engine_result_v(engine_result_v),.engine_result_tag(engine_result_tag),.engine_result_gen(engine_result_gen),.engine_result_done(engine_result_done),.engine_result_fault(engine_result_fault),.engine_result_cause(engine_result_cause),.engine_result_token(engine_result_token),.engine_result_value(engine_result_value),.engine_result_cycles(engine_result_cycles),.engine_result_cr(engine_result_cr),
 .program_consensus(program_consensus),.program_epoch(program_epoch),.program_digest(program_digest),.certificate_valid(),.certificate(),.certificate_prefix(),.wrap_locked(wrap_locked),.identity_fault(identity_fault),.recovery_complete(recovery_complete),.post_pending(post_pending),.fault(fault));
 if(1)begin:g_rank_0
  qkd_host_peer_rank_codec #(.RANK(0))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[0]),.tx_data(peer_rx_data[0*512+:512]),.tx_ready(peer_rx_ready[0]),.rx_valid(peer_tx_valid[0]),.rx_data(peer_tx_data[0*512+:512]),.rx_ready(peer_tx_ready[0]),
  .request_v(request_v[0]),.request_tag(request_tag[0*59+:59]),.request_gen(request_gen[0*2+:2]),.request_trace(request_trace[0*32+:32]),.request_token(request_token[0*18+:18]),.request_pos(request_pos[0*18+:18]),.request_cr(request_cr[0]),.request_aborted(),
  .cancel_valid(cancel_offer[0]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[0]}}),.cancel_accepted(cancel_ack[0]),.cancel_release_v(release_v[0]),.cancel_release_tag(release_tag[0*59+:59]),.cancel_release_gen(release_gen[0*2+:2]),.cancel_released(cancel_released[0]),
  .result_v(result_v[0]),.result_tag(result_tag[0*59+:59]),.result_gen(result_gen[0*2+:2]),.result_done(result_done[0]),.result_fault(result_fault[0]),.result_cause(result_cause[0*4+:4]),.result_token(result_token[0*18+:18]),.result_value(result_value[0*32+:32]),.result_cycles(result_cycles[0*32+:32]),.result_cr(result_credit[0]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[0]}}),.context_owned(context_owned[0]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(0==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(0==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(0==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[0]),.retrain_request(retrain_request[0]),.recovery_clear(recovery_clear[0]),.fault(codec_fault[0]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[0]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[0]),.request_tag(request_tag[0*59+:59]),.request_trace(request_trace[0*32+:32]),.request_gen(request_gen[0*2+:2]),.request_token(request_token[0*18+:18]),.request_pos(request_pos[0*18+:18]),.request_cr(request_cr[0]),.native_pr(),
  .result_v(result_v[0]),.result_tag(result_tag[0*59+:59]),.result_gen(result_gen[0*2+:2]),.result_done(result_done[0]),.result_fault(result_fault[0]),.result_cause(result_cause[0*4+:4]),.result_token(result_token[0*18+:18]),.result_value(result_value[0*32+:32]),.result_cycles(result_cycles[0*32+:32]),.result_cr(result_credit[0]),
  .kv_drained(drains[0]),.vm_drained(drains[0]),.collective_drained(drains[0]),.host_drained(drains[0]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[0]),.cancel_release_v(release_v[0]),.cancel_release_tag(release_tag[0*59+:59]),.cancel_release_gen(release_gen[0*2+:2]),.context_owned(context_owned[0]),.cancel_released(cancel_released[0]),.local_tk(tk[0*93+:93]),.protocol_fault(endpoint_fault[0]));
  end
 if(1)begin:g_rank_1
  qkd_host_peer_rank_codec #(.RANK(1))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[1]),.tx_data(peer_rx_data[1*512+:512]),.tx_ready(peer_rx_ready[1]),.rx_valid(peer_tx_valid[1]),.rx_data(peer_tx_data[1*512+:512]),.rx_ready(peer_tx_ready[1]),
  .request_v(request_v[1]),.request_tag(request_tag[1*59+:59]),.request_gen(request_gen[1*2+:2]),.request_trace(request_trace[1*32+:32]),.request_token(request_token[1*18+:18]),.request_pos(request_pos[1*18+:18]),.request_cr(request_cr[1]),.request_aborted(),
  .cancel_valid(cancel_offer[1]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[1]}}),.cancel_accepted(cancel_ack[1]),.cancel_release_v(release_v[1]),.cancel_release_tag(release_tag[1*59+:59]),.cancel_release_gen(release_gen[1*2+:2]),.cancel_released(cancel_released[1]),
  .result_v(result_v[1]),.result_tag(result_tag[1*59+:59]),.result_gen(result_gen[1*2+:2]),.result_done(result_done[1]),.result_fault(result_fault[1]),.result_cause(result_cause[1*4+:4]),.result_token(result_token[1*18+:18]),.result_value(result_value[1*32+:32]),.result_cycles(result_cycles[1*32+:32]),.result_cr(result_credit[1]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[1]}}),.context_owned(context_owned[1]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(1==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(1==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(1==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[1]),.retrain_request(retrain_request[1]),.recovery_clear(recovery_clear[1]),.fault(codec_fault[1]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[1]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[1]),.request_tag(request_tag[1*59+:59]),.request_trace(request_trace[1*32+:32]),.request_gen(request_gen[1*2+:2]),.request_token(request_token[1*18+:18]),.request_pos(request_pos[1*18+:18]),.request_cr(request_cr[1]),.native_pr(),
  .result_v(result_v[1]),.result_tag(result_tag[1*59+:59]),.result_gen(result_gen[1*2+:2]),.result_done(result_done[1]),.result_fault(result_fault[1]),.result_cause(result_cause[1*4+:4]),.result_token(result_token[1*18+:18]),.result_value(result_value[1*32+:32]),.result_cycles(result_cycles[1*32+:32]),.result_cr(result_credit[1]),
  .kv_drained(drains[1]),.vm_drained(drains[1]),.collective_drained(drains[1]),.host_drained(drains[1]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[1]),.cancel_release_v(release_v[1]),.cancel_release_tag(release_tag[1*59+:59]),.cancel_release_gen(release_gen[1*2+:2]),.context_owned(context_owned[1]),.cancel_released(cancel_released[1]),.local_tk(tk[1*93+:93]),.protocol_fault(endpoint_fault[1]));
  end
 if(1)begin:g_rank_2
  qkd_host_peer_rank_codec #(.RANK(2))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[2]),.tx_data(peer_rx_data[2*512+:512]),.tx_ready(peer_rx_ready[2]),.rx_valid(peer_tx_valid[2]),.rx_data(peer_tx_data[2*512+:512]),.rx_ready(peer_tx_ready[2]),
  .request_v(request_v[2]),.request_tag(request_tag[2*59+:59]),.request_gen(request_gen[2*2+:2]),.request_trace(request_trace[2*32+:32]),.request_token(request_token[2*18+:18]),.request_pos(request_pos[2*18+:18]),.request_cr(request_cr[2]),.request_aborted(),
  .cancel_valid(cancel_offer[2]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[2]}}),.cancel_accepted(cancel_ack[2]),.cancel_release_v(release_v[2]),.cancel_release_tag(release_tag[2*59+:59]),.cancel_release_gen(release_gen[2*2+:2]),.cancel_released(cancel_released[2]),
  .result_v(result_v[2]),.result_tag(result_tag[2*59+:59]),.result_gen(result_gen[2*2+:2]),.result_done(result_done[2]),.result_fault(result_fault[2]),.result_cause(result_cause[2*4+:4]),.result_token(result_token[2*18+:18]),.result_value(result_value[2*32+:32]),.result_cycles(result_cycles[2*32+:32]),.result_cr(result_credit[2]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[2]}}),.context_owned(context_owned[2]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(2==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(2==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(2==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[2]),.retrain_request(retrain_request[2]),.recovery_clear(recovery_clear[2]),.fault(codec_fault[2]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[2]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[2]),.request_tag(request_tag[2*59+:59]),.request_trace(request_trace[2*32+:32]),.request_gen(request_gen[2*2+:2]),.request_token(request_token[2*18+:18]),.request_pos(request_pos[2*18+:18]),.request_cr(request_cr[2]),.native_pr(),
  .result_v(result_v[2]),.result_tag(result_tag[2*59+:59]),.result_gen(result_gen[2*2+:2]),.result_done(result_done[2]),.result_fault(result_fault[2]),.result_cause(result_cause[2*4+:4]),.result_token(result_token[2*18+:18]),.result_value(result_value[2*32+:32]),.result_cycles(result_cycles[2*32+:32]),.result_cr(result_credit[2]),
  .kv_drained(drains[2]),.vm_drained(drains[2]),.collective_drained(drains[2]),.host_drained(drains[2]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[2]),.cancel_release_v(release_v[2]),.cancel_release_tag(release_tag[2*59+:59]),.cancel_release_gen(release_gen[2*2+:2]),.context_owned(context_owned[2]),.cancel_released(cancel_released[2]),.local_tk(tk[2*93+:93]),.protocol_fault(endpoint_fault[2]));
  end
 if(1)begin:g_rank_3
  qkd_host_peer_rank_codec #(.RANK(3))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[3]),.tx_data(peer_rx_data[3*512+:512]),.tx_ready(peer_rx_ready[3]),.rx_valid(peer_tx_valid[3]),.rx_data(peer_tx_data[3*512+:512]),.rx_ready(peer_tx_ready[3]),
  .request_v(request_v[3]),.request_tag(request_tag[3*59+:59]),.request_gen(request_gen[3*2+:2]),.request_trace(request_trace[3*32+:32]),.request_token(request_token[3*18+:18]),.request_pos(request_pos[3*18+:18]),.request_cr(request_cr[3]),.request_aborted(),
  .cancel_valid(cancel_offer[3]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[3]}}),.cancel_accepted(cancel_ack[3]),.cancel_release_v(release_v[3]),.cancel_release_tag(release_tag[3*59+:59]),.cancel_release_gen(release_gen[3*2+:2]),.cancel_released(cancel_released[3]),
  .result_v(result_v[3]),.result_tag(result_tag[3*59+:59]),.result_gen(result_gen[3*2+:2]),.result_done(result_done[3]),.result_fault(result_fault[3]),.result_cause(result_cause[3*4+:4]),.result_token(result_token[3*18+:18]),.result_value(result_value[3*32+:32]),.result_cycles(result_cycles[3*32+:32]),.result_cr(result_credit[3]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[3]}}),.context_owned(context_owned[3]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(3==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(3==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(3==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[3]),.retrain_request(retrain_request[3]),.recovery_clear(recovery_clear[3]),.fault(codec_fault[3]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[3]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[3]),.request_tag(request_tag[3*59+:59]),.request_trace(request_trace[3*32+:32]),.request_gen(request_gen[3*2+:2]),.request_token(request_token[3*18+:18]),.request_pos(request_pos[3*18+:18]),.request_cr(request_cr[3]),.native_pr(),
  .result_v(result_v[3]),.result_tag(result_tag[3*59+:59]),.result_gen(result_gen[3*2+:2]),.result_done(result_done[3]),.result_fault(result_fault[3]),.result_cause(result_cause[3*4+:4]),.result_token(result_token[3*18+:18]),.result_value(result_value[3*32+:32]),.result_cycles(result_cycles[3*32+:32]),.result_cr(result_credit[3]),
  .kv_drained(drains[3]),.vm_drained(drains[3]),.collective_drained(drains[3]),.host_drained(drains[3]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[3]),.cancel_release_v(release_v[3]),.cancel_release_tag(release_tag[3*59+:59]),.cancel_release_gen(release_gen[3*2+:2]),.context_owned(context_owned[3]),.cancel_released(cancel_released[3]),.local_tk(tk[3*93+:93]),.protocol_fault(endpoint_fault[3]));
  end
 if(1)begin:g_rank_4
  qkd_host_peer_rank_codec #(.RANK(4))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[4]),.tx_data(peer_rx_data[4*512+:512]),.tx_ready(peer_rx_ready[4]),.rx_valid(peer_tx_valid[4]),.rx_data(peer_tx_data[4*512+:512]),.rx_ready(peer_tx_ready[4]),
  .request_v(request_v[4]),.request_tag(request_tag[4*59+:59]),.request_gen(request_gen[4*2+:2]),.request_trace(request_trace[4*32+:32]),.request_token(request_token[4*18+:18]),.request_pos(request_pos[4*18+:18]),.request_cr(request_cr[4]),.request_aborted(),
  .cancel_valid(cancel_offer[4]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[4]}}),.cancel_accepted(cancel_ack[4]),.cancel_release_v(release_v[4]),.cancel_release_tag(release_tag[4*59+:59]),.cancel_release_gen(release_gen[4*2+:2]),.cancel_released(cancel_released[4]),
  .result_v(result_v[4]),.result_tag(result_tag[4*59+:59]),.result_gen(result_gen[4*2+:2]),.result_done(result_done[4]),.result_fault(result_fault[4]),.result_cause(result_cause[4*4+:4]),.result_token(result_token[4*18+:18]),.result_value(result_value[4*32+:32]),.result_cycles(result_cycles[4*32+:32]),.result_cr(result_credit[4]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[4]}}),.context_owned(context_owned[4]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(4==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(4==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(4==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[4]),.retrain_request(retrain_request[4]),.recovery_clear(recovery_clear[4]),.fault(codec_fault[4]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[4]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[4]),.request_tag(request_tag[4*59+:59]),.request_trace(request_trace[4*32+:32]),.request_gen(request_gen[4*2+:2]),.request_token(request_token[4*18+:18]),.request_pos(request_pos[4*18+:18]),.request_cr(request_cr[4]),.native_pr(),
  .result_v(result_v[4]),.result_tag(result_tag[4*59+:59]),.result_gen(result_gen[4*2+:2]),.result_done(result_done[4]),.result_fault(result_fault[4]),.result_cause(result_cause[4*4+:4]),.result_token(result_token[4*18+:18]),.result_value(result_value[4*32+:32]),.result_cycles(result_cycles[4*32+:32]),.result_cr(result_credit[4]),
  .kv_drained(drains[4]),.vm_drained(drains[4]),.collective_drained(drains[4]),.host_drained(drains[4]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[4]),.cancel_release_v(release_v[4]),.cancel_release_tag(release_tag[4*59+:59]),.cancel_release_gen(release_gen[4*2+:2]),.context_owned(context_owned[4]),.cancel_released(cancel_released[4]),.local_tk(tk[4*93+:93]),.protocol_fault(endpoint_fault[4]));
  end
 if(1)begin:g_rank_5
  qkd_host_peer_rank_codec #(.RANK(5))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[5]),.tx_data(peer_rx_data[5*512+:512]),.tx_ready(peer_rx_ready[5]),.rx_valid(peer_tx_valid[5]),.rx_data(peer_tx_data[5*512+:512]),.rx_ready(peer_tx_ready[5]),
  .request_v(request_v[5]),.request_tag(request_tag[5*59+:59]),.request_gen(request_gen[5*2+:2]),.request_trace(request_trace[5*32+:32]),.request_token(request_token[5*18+:18]),.request_pos(request_pos[5*18+:18]),.request_cr(request_cr[5]),.request_aborted(),
  .cancel_valid(cancel_offer[5]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[5]}}),.cancel_accepted(cancel_ack[5]),.cancel_release_v(release_v[5]),.cancel_release_tag(release_tag[5*59+:59]),.cancel_release_gen(release_gen[5*2+:2]),.cancel_released(cancel_released[5]),
  .result_v(result_v[5]),.result_tag(result_tag[5*59+:59]),.result_gen(result_gen[5*2+:2]),.result_done(result_done[5]),.result_fault(result_fault[5]),.result_cause(result_cause[5*4+:4]),.result_token(result_token[5*18+:18]),.result_value(result_value[5*32+:32]),.result_cycles(result_cycles[5*32+:32]),.result_cr(result_credit[5]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[5]}}),.context_owned(context_owned[5]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(5==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(5==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(5==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[5]),.retrain_request(retrain_request[5]),.recovery_clear(recovery_clear[5]),.fault(codec_fault[5]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[5]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[5]),.request_tag(request_tag[5*59+:59]),.request_trace(request_trace[5*32+:32]),.request_gen(request_gen[5*2+:2]),.request_token(request_token[5*18+:18]),.request_pos(request_pos[5*18+:18]),.request_cr(request_cr[5]),.native_pr(),
  .result_v(result_v[5]),.result_tag(result_tag[5*59+:59]),.result_gen(result_gen[5*2+:2]),.result_done(result_done[5]),.result_fault(result_fault[5]),.result_cause(result_cause[5*4+:4]),.result_token(result_token[5*18+:18]),.result_value(result_value[5*32+:32]),.result_cycles(result_cycles[5*32+:32]),.result_cr(result_credit[5]),
  .kv_drained(drains[5]),.vm_drained(drains[5]),.collective_drained(drains[5]),.host_drained(drains[5]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[5]),.cancel_release_v(release_v[5]),.cancel_release_tag(release_tag[5*59+:59]),.cancel_release_gen(release_gen[5*2+:2]),.context_owned(context_owned[5]),.cancel_released(cancel_released[5]),.local_tk(tk[5*93+:93]),.protocol_fault(endpoint_fault[5]));
  end
 if(1)begin:g_rank_6
  qkd_host_peer_rank_codec #(.RANK(6))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[6]),.tx_data(peer_rx_data[6*512+:512]),.tx_ready(peer_rx_ready[6]),.rx_valid(peer_tx_valid[6]),.rx_data(peer_tx_data[6*512+:512]),.rx_ready(peer_tx_ready[6]),
  .request_v(request_v[6]),.request_tag(request_tag[6*59+:59]),.request_gen(request_gen[6*2+:2]),.request_trace(request_trace[6*32+:32]),.request_token(request_token[6*18+:18]),.request_pos(request_pos[6*18+:18]),.request_cr(request_cr[6]),.request_aborted(),
  .cancel_valid(cancel_offer[6]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[6]}}),.cancel_accepted(cancel_ack[6]),.cancel_release_v(release_v[6]),.cancel_release_tag(release_tag[6*59+:59]),.cancel_release_gen(release_gen[6*2+:2]),.cancel_released(cancel_released[6]),
  .result_v(result_v[6]),.result_tag(result_tag[6*59+:59]),.result_gen(result_gen[6*2+:2]),.result_done(result_done[6]),.result_fault(result_fault[6]),.result_cause(result_cause[6*4+:4]),.result_token(result_token[6*18+:18]),.result_value(result_value[6*32+:32]),.result_cycles(result_cycles[6*32+:32]),.result_cr(result_credit[6]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[6]}}),.context_owned(context_owned[6]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(6==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(6==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(6==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[6]),.retrain_request(retrain_request[6]),.recovery_clear(recovery_clear[6]),.fault(codec_fault[6]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[6]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[6]),.request_tag(request_tag[6*59+:59]),.request_trace(request_trace[6*32+:32]),.request_gen(request_gen[6*2+:2]),.request_token(request_token[6*18+:18]),.request_pos(request_pos[6*18+:18]),.request_cr(request_cr[6]),.native_pr(),
  .result_v(result_v[6]),.result_tag(result_tag[6*59+:59]),.result_gen(result_gen[6*2+:2]),.result_done(result_done[6]),.result_fault(result_fault[6]),.result_cause(result_cause[6*4+:4]),.result_token(result_token[6*18+:18]),.result_value(result_value[6*32+:32]),.result_cycles(result_cycles[6*32+:32]),.result_cr(result_credit[6]),
  .kv_drained(drains[6]),.vm_drained(drains[6]),.collective_drained(drains[6]),.host_drained(drains[6]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[6]),.cancel_release_v(release_v[6]),.cancel_release_tag(release_tag[6*59+:59]),.cancel_release_gen(release_gen[6*2+:2]),.context_owned(context_owned[6]),.cancel_released(cancel_released[6]),.local_tk(tk[6*93+:93]),.protocol_fault(endpoint_fault[6]));
  end
 if(1)begin:g_rank_7
  qkd_host_peer_rank_codec #(.RANK(7))codec(.ck(ck),.por_n(por_n),.tx_valid(peer_rx_valid[7]),.tx_data(peer_rx_data[7*512+:512]),.tx_ready(peer_rx_ready[7]),.rx_valid(peer_tx_valid[7]),.rx_data(peer_tx_data[7*512+:512]),.rx_ready(peer_tx_ready[7]),
  .request_v(request_v[7]),.request_tag(request_tag[7*59+:59]),.request_gen(request_gen[7*2+:2]),.request_trace(request_trace[7*32+:32]),.request_token(request_token[7*18+:18]),.request_pos(request_pos[7*18+:18]),.request_cr(request_cr[7]),.request_aborted(),
  .cancel_valid(cancel_offer[7]),.cancel_tag(engine_result_tag),.cancel_gen(token_grant_gen),.cancel_done(1'b0),.cancel_fault(1'b1),.cancel_drained({4{drains[7]}}),.cancel_accepted(cancel_ack[7]),.cancel_release_v(release_v[7]),.cancel_release_tag(release_tag[7*59+:59]),.cancel_release_gen(release_gen[7*2+:2]),.cancel_released(cancel_released[7]),
  .result_v(result_v[7]),.result_tag(result_tag[7*59+:59]),.result_gen(result_gen[7*2+:2]),.result_done(result_done[7]),.result_fault(result_fault[7]),.result_cause(result_cause[7*4+:4]),.result_token(result_token[7*18+:18]),.result_value(result_value[7*32+:32]),.result_cycles(result_cycles[7*32+:32]),.result_cr(result_credit[7]),
  .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drains[7]}}),.context_owned(context_owned[7]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
  .step_issue_v(7==0&&step_issue_v),.step_client_tag(16'h7261),.step_slot(8'd0),.step_pos(pos),.step_retire_v(7==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(16'h7261),.step_retire_slot(8'd0),.step_retire_pos(pos),.step_retire_token(engine_result_token),
  .cq_commit_v(7==0&&cq_commit_v),.cq_client_tag(16'h7261),.cq_slot(8'd0),.cq_pos(pos),.cq_token(engine_result_token),.certificate_v(certificate_v),.certificate(66'h1234),.certificate_prefix(32'd0),
  .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(reset_request[7]),.retrain_request(retrain_request[7]),.recovery_clear(recovery_clear[7]),.fault(codec_fault[7]));
  qkd_host_native_token_endpoint_cancel #(.ENABLE_NATIVE(1))endpoint(.ck(ck),.por_n(por_n),.rst_n(por_n),.hc(hc_mask[7]?hc:182'd0),.legacy_tk(93'd0),.image_ready(1'b1),.shared_epoch_valid(shared_epoch_valid),.shared_epoch(shared_epoch),
  .request_v(request_v[7]),.request_tag(request_tag[7*59+:59]),.request_trace(request_trace[7*32+:32]),.request_gen(request_gen[7*2+:2]),.request_token(request_token[7*18+:18]),.request_pos(request_pos[7*18+:18]),.request_cr(request_cr[7]),.native_pr(),
  .result_v(result_v[7]),.result_tag(result_tag[7*59+:59]),.result_gen(result_gen[7*2+:2]),.result_done(result_done[7]),.result_fault(result_fault[7]),.result_cause(result_cause[7*4+:4]),.result_token(result_token[7*18+:18]),.result_value(result_value[7*32+:32]),.result_cycles(result_cycles[7*32+:32]),.result_cr(result_credit[7]),
  .kv_drained(drains[7]),.vm_drained(drains[7]),.collective_drained(drains[7]),.host_drained(drains[7]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[7]),.cancel_release_v(release_v[7]),.cancel_release_tag(release_tag[7*59+:59]),.cancel_release_gen(release_gen[7*2+:2]),.context_owned(context_owned[7]),.cancel_released(cancel_released[7]),.local_tk(tk[7*93+:93]),.protocol_fault(endpoint_fault[7]));
  end
 integer terminals=0,results=0;integer k;
 always @(negedge ck)if(por_n)begin
  if(engine_result_cr)results=results+1;
  cancel_offer=cancel_offer&~cancel_ack;
  for(k=0;k<8;k=k+1)if(cancel_released[k])release_count=release_count+1;
  if(fault||(|codec_fault)||(|endpoint_fault))$fatal(1,"protocol fault root=%b identity=%b post=%b codec=%h endpoint=%h",fault,identity_fault,post_pending,codec_fault,endpoint_fault);
 end
 task ticks(input integer n);repeat(n)begin @(posedge ck);#1;end endtask
 task launch(input integer p,input[7:0]mask,input bit complete);begin
  while(!token_request_ready)ticks(1);
  @(negedge ck);hc_mask=mask;pos=p;step_issue_v=1;token_request_position=p;token_request_valid=1;
  ticks(1);@(negedge ck);step_issue_v=0;
  @(negedge ck);token_request_valid=0;
  wait(token_grant_valid);@(negedge ck);token_grant_ready=1;ticks(1);@(negedge ck);token_grant_ready=0;
  shared_epoch=token_grant_epoch;shared_epoch_valid=1;hc[38]=1;hc[37:36]=token_grant_gen;hc[35:18]=token_grant_token;hc[17:0]=token_grant_position;
  ticks(1);@(negedge ck);hc[38]=0;shared_epoch_valid=0;
  if(complete)begin wait(dispatched);ticks(3);if(accepted_ranks!=255)$fatal(1,"partial real cohort dispatch");end else ticks(12);
 end endtask
 initial begin
  ticks(4);@(negedge ck);por_n=1;ticks(4);@(negedge ck);certificate_v=1;ticks(1);@(negedge ck);certificate_v=0;
  wait(token_request_ready);launch(0,255,1);
  @(negedge ck);engine_result_tag={token_grant_tag[58:43],6'd37,token_grant_tag[36:0]};engine_result_gen=token_grant_gen;engine_result_done=1;engine_result_v=1;
  ticks(1);@(negedge ck);engine_result_v=0;
  wait(results==1);ticks(10);@(negedge ck);step_retire_v=1;step_retire_cq=0;ticks(1);@(negedge ck);step_retire_v=0;
  wait(token_request_ready);if(context_owned!=0)$fatal(1,"POST admitted live context");
  launch(1,255,1);@(negedge ck);engine_result_tag={token_grant_tag[58:43],6'd37,token_grant_tag[36:0]};engine_result_gen=token_grant_gen;engine_result_v=1;
  ticks(1);@(negedge ck);engine_result_v=0;wait(results==2);ticks(10);@(negedge ck);step_retire_v=1;step_retire_cq=1;ticks(1);@(negedge ck);step_retire_v=0;
  ticks(40);if(token_request_ready||!post_pending)$fatal(1,"generated step skipped genuine CQ commit requirement");
  @(negedge ck);cq_commit_v=1;ticks(1);@(negedge ck);cq_commit_v=0;
  wait(token_request_ready);ticks(5);if(context_owned!=0||results!=2)$fatal(1,"result/context ownership mismatch");
  // Cancellation before a complete cohort: four real contexts exist, four
  // are genuinely empty. Neither case creates a fake result-slot return.
  launch(2,8'h0f,0);
  if(dispatched||accepted_ranks!=15||context_owned!=15)$fatal(1,"partial cohort fixture mismatch");
  @(negedge ck);engine_result_tag={token_grant_tag[58:43],6'd37,token_grant_tag[36:0]};cancel_offer=1;
  wait(post_pending);wait(release_count==24);ticks(20);
  if(!post_pending||context_owned!=0||results!=2||token_request_ready)$fatal(1,"cancel omitted actual HOST fault CQ");
  @(negedge ck);step_retire_v=1;step_retire_cq=1;ticks(1);@(negedge ck);step_retire_v=0;
  ticks(20);if(!post_pending)$fatal(1,"cancel skipped fault CQ commit");
  @(negedge ck);cq_commit_v=1;ticks(1);@(negedge ck);cq_commit_v=0;
  wait(!post_pending);ticks(20);
  if(context_owned!=0||release_count!=24||results!=2||token_request_ready||recovery_complete)$fatal(1,"cancel/barrier fabricated completion or recovery");
  wait(reset_request==255);ticks(5);if(recovery_complete)$fatal(1,"recovery completed with no physical reset witnesses");
  $display("PASS HOST_PEER_LIFECYCLE protocol_boundary=1 real_cohort=8 real_result_returns=16 terminal_certificates=24 prefill_and_generated_POST=2 partial_cancel=4_real_4_empty recovery_blocked_without_reset=1");$finish;
 end
 initial begin #200000;$fatal(1,"peer lifecycle timeout ready=%b grant=%b dispatched=%b post=%b owned=%h results=%0d",token_request_ready,token_grant_valid,dispatched,post_pending,context_owned,results);end
endmodule
