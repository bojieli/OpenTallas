`timescale 1ns/1ps
// KV-HOST/PEER r6 (10-19): qkd_host_peer_coordinator_codec_pd vs the unchanged qkd_host_peer_coordinator_codec whose
// allocated_* inputs pass the same one-edge register (async-cleared by por_n) in this bench.  Random allocation changes
// (sparse), random tx_ready, well-formed class9 RX words (status 3, request 1 against the live allocation, cancel 2,
// certificate 9, result returns 4) with per-rank sequence plus ~1% corrupt words, result / terminal / post pulses and
// random por_n pulses.  Every output compared every edge (4-state).  -DQKD_HR_PE_CPD_MUTANT must FAIL.
module tb_hr_peer_codec_pd;
 parameter integer NCYC=200000, SEED=1019;
 reg ck=0; always #5 ck=~ck;
 reg por_n=0;
 reg[7:0]rx_valid=0; reg[4095:0]rx_data=0; reg[7:0]tx_ready=0;
 reg allocated_valid=0,allocated_delivered=0; reg[58:0]allocated_tag=0; reg[1:0]allocated_gen=0; reg[17:0]allocated_position=0;
 reg[7:0]participant_accepted=0,cancel_accepted=0;
 reg result_v=0; reg[58:0]result_tag=0; reg[1:0]result_gen=0; reg result_done=0,result_fault=0; reg[3:0]result_cause=0;
 reg[17:0]result_token=0; reg[31:0]result_value=0,result_cycles=0;
 reg terminal_accepted=0; reg[58:0]terminal_tag=0; reg[1:0]terminal_gen=0; reg post_retired=0, link_reset_request=0, retraining_request=0;
 // the reference's one-edge allocation delay (por_n-cleared, as the fork's stage)
 reg d_v,d_d; reg[58:0]d_tag; reg[1:0]d_gen; reg[17:0]d_pos;
 always @(posedge ck or negedge por_n) if(!por_n) {d_pos,d_gen,d_tag,d_d,d_v}<=0;
  else {d_pos,d_gen,d_tag,d_d,d_v}<={allocated_position,allocated_gen,allocated_tag,allocated_delivered,allocated_valid};
`define CPD_DECL(p) \
 wire[7:0]p``rx_ready,p``tx_valid; wire[4095:0]p``tx_data; wire[7:0]p``participant_valid; wire[471:0]p``participant_tag; wire[15:0]p``participant_gen; \
 wire[255:0]p``participant_trace; wire[143:0]p``participant_token,p``participant_pos; wire[7:0]p``cancel_valid,p``cancel_done,p``cancel_fault; \
 wire[471:0]p``cancel_tag; wire[15:0]p``cancel_gen; \
 wire[7:0]p``service_ready,p``native_ready,p``kv_drained,p``vm_drained,p``collective_drained,p``host_drained,p``context_owned,p``links_drained,p``link_reset_seen,p``retrained; \
 wire[127:0]p``service_epoch,p``certificate_epoch; wire[7:0]p``program_ready; wire[127:0]p``program_epoch; wire[511:0]p``program_digest; \
 wire p``result_cr; wire[7:0]p``terminal_released; wire p``result_transport_idle; \
 wire p``step_issue_v; wire[15:0]p``step_client_tag; wire[7:0]p``step_slot; wire[17:0]p``step_pos; \
 wire p``step_retire_v,p``step_retire_cq; wire[15:0]p``step_retire_client_tag; wire[7:0]p``step_retire_slot; wire[17:0]p``step_retire_pos,p``step_retire_token; \
 wire p``cq_commit_v; wire[15:0]p``cq_client_tag; wire[7:0]p``cq_slot; wire[17:0]p``cq_pos,p``cq_token; \
 wire[7:0]p``certificate_valid; wire[527:0]p``certificate; wire[255:0]p``certificate_prefix; wire p``fault; \
 wire[7600:0] p``all={p``rx_ready,p``tx_valid,p``tx_data,p``participant_valid,p``participant_tag,p``participant_gen,p``participant_trace,p``participant_token, \
  p``participant_pos,p``cancel_valid,p``cancel_done,p``cancel_fault,p``cancel_tag,p``cancel_gen,p``service_ready,p``native_ready,p``kv_drained,p``vm_drained, \
  p``collective_drained,p``host_drained,p``context_owned,p``links_drained,p``link_reset_seen,p``retrained,p``service_epoch,p``certificate_epoch,p``program_ready, \
  p``program_epoch,p``program_digest,p``result_cr,p``terminal_released,p``result_transport_idle,p``step_issue_v,p``step_client_tag,p``step_slot,p``step_pos, \
  p``step_retire_v,p``step_retire_cq,p``step_retire_client_tag,p``step_retire_slot,p``step_retire_pos,p``step_retire_token,p``cq_commit_v,p``cq_client_tag, \
  p``cq_slot,p``cq_pos,p``cq_token,p``certificate_valid,p``certificate,p``certificate_prefix,p``fault};
`define CPD_OUT(p) \
 .rx_ready(p``rx_ready),.tx_valid(p``tx_valid),.tx_data(p``tx_data),.participant_valid(p``participant_valid),.participant_tag(p``participant_tag), \
 .participant_gen(p``participant_gen),.participant_trace(p``participant_trace),.participant_token(p``participant_token),.participant_pos(p``participant_pos), \
 .cancel_valid(p``cancel_valid),.cancel_done(p``cancel_done),.cancel_fault(p``cancel_fault),.cancel_tag(p``cancel_tag),.cancel_gen(p``cancel_gen), \
 .service_ready(p``service_ready),.native_ready(p``native_ready),.kv_drained(p``kv_drained),.vm_drained(p``vm_drained),.collective_drained(p``collective_drained), \
 .host_drained(p``host_drained),.context_owned(p``context_owned),.links_drained(p``links_drained),.link_reset_seen(p``link_reset_seen),.retrained(p``retrained), \
 .service_epoch(p``service_epoch),.certificate_epoch(p``certificate_epoch),.program_ready(p``program_ready),.program_epoch(p``program_epoch),.program_digest(p``program_digest), \
 .result_cr(p``result_cr),.terminal_released(p``terminal_released),.result_transport_idle(p``result_transport_idle),.step_issue_v(p``step_issue_v), \
 .step_client_tag(p``step_client_tag),.step_slot(p``step_slot),.step_pos(p``step_pos),.step_retire_v(p``step_retire_v),.step_retire_cq(p``step_retire_cq), \
 .step_retire_client_tag(p``step_retire_client_tag),.step_retire_slot(p``step_retire_slot),.step_retire_pos(p``step_retire_pos),.step_retire_token(p``step_retire_token), \
 .cq_commit_v(p``cq_commit_v),.cq_client_tag(p``cq_client_tag),.cq_slot(p``cq_slot),.cq_pos(p``cq_pos),.cq_token(p``cq_token),.certificate_valid(p``certificate_valid), \
 .certificate(p``certificate),.certificate_prefix(p``certificate_prefix),.fault(p``fault)
`define CPD_IN \
 .ck(ck),.por_n(por_n),.rx_valid(rx_valid),.rx_data(rx_data),.tx_ready(tx_ready),.participant_accepted(participant_accepted),.cancel_accepted(cancel_accepted), \
 .result_v(result_v),.result_tag(result_tag),.result_gen(result_gen),.result_done(result_done),.result_fault(result_fault),.result_cause(result_cause), \
 .result_token(result_token),.result_value(result_value),.result_cycles(result_cycles),.terminal_accepted(terminal_accepted),.terminal_tag(terminal_tag), \
 .terminal_gen(terminal_gen),.post_retired(post_retired),.link_reset_request(link_reset_request),.retraining_request(retraining_request)
 `CPD_DECL(a_)
 `CPD_DECL(b_)
 qkd_host_peer_coordinator_codec ua(`CPD_IN,`CPD_OUT(a_),.allocated_valid(d_v),.allocated_delivered(d_d),.allocated_tag(d_tag),.allocated_gen(d_gen),.allocated_position(d_pos));
 qkd_host_peer_coordinator_codec_pd ub(`CPD_IN,`CPD_OUT(b_),.allocated_valid_i(allocated_valid),.allocated_delivered_i(allocated_delivered),
  .allocated_tag_i(allocated_tag),.allocated_gen_i(allocated_gen),.allocated_position_i(allocated_position));
 integer seed, cyc, mism=0, first=-1, resets=0, sends6=0, rxacc=0, i, k;
 reg[15:0] seq[0:7]; reg[511:0] w;
 task automatic do_reset; begin por_n=0; resets=resets+1; for(i=0;i<8;i=i+1)seq[i]=0; @(posedge ck); #1; @(posedge ck); #1 por_n=1; end endtask
 initial begin
  seed=SEED; for(i=0;i<8;i=i+1)seq[i]=0;
  repeat(3) @(posedge ck); #1 por_n=1;
  for(cyc=0;cyc<NCYC;cyc=cyc+1) begin
   @(negedge ck); if(a_all!==b_all) begin mism=mism+1; if(first<0) first=cyc; if(mism<4) $display("MISMATCH cyc %0d fault %b/%b tx_valid %h/%h", cyc, a_fault, b_fault, a_tx_valid, b_tx_valid); end
   @(posedge ck); #1;
   for(i=0;i<8;i=i+1) if(ua.tx_valid[i]&&tx_ready[i]&&ua.choice[i]==6) sends6=sends6+1;
   for(i=0;i<8;i=i+1) if(rx_valid[i]&&a_rx_ready[i]) begin seq[i]=seq[i]+1; rxacc=rxacc+1; end
   if(a_fault && ($random(seed)&15)==0) do_reset();
   if(($random(seed)&2047)==0) do_reset();
   tx_ready=$random(seed);
   if(($random(seed)&15)==0) begin allocated_valid=$random(seed); allocated_delivered=$random(seed);
    allocated_tag={$random(seed),$random(seed)}; allocated_gen=$random(seed); allocated_position=$random(seed); end
   link_reset_request=(($random(seed)&255)==0)?~link_reset_request:link_reset_request;
   retraining_request=(($random(seed)&255)==0)?~retraining_request:retraining_request;
   participant_accepted=0; cancel_accepted=0;
   for(i=0;i<8;i=i+1) begin
    if(ua.participant_valid[i]||(ua.request_queued[i]&&($random(seed)&7)==0)) participant_accepted[i]=($random(seed)&3)==0 && ua.request_queued[i] && !ua.request_ack[i];
    if(ua.cancel_valid[i]) cancel_accepted[i]=($random(seed)&3)==0;
   end
   result_v=(($random(seed)&127)==0); result_done=$random(seed); result_fault=(($random(seed)&15)==0); result_tag={$random(seed),$random(seed)};
   result_gen=$random(seed); result_cause=$random(seed); result_token=$random(seed); result_value=$random(seed); result_cycles=$random(seed);
   terminal_accepted=(($random(seed)&255)==0); terminal_tag={$random(seed),$random(seed)}; terminal_gen=$random(seed);
   post_retired=(($random(seed)&255)==0);
   rx_valid=0; rx_data=0;
   for(i=0;i<8;i=i+1) if(($random(seed)&7)==0) begin
    w=0; k={$random(seed)}%10;
    w[10:8]=i; w[29:14]=seq[i];
    case(k)
     0,1,2: begin w[7:0]=3; w[136:30]={$random(seed),$random(seed),$random(seed),$random(seed)}; end
     3,4: begin w[7:0]=1; w[88:30]=ua.allocated_tag; w[90:89]=ua.allocated_gen; w[158:91]={$random(seed),$random(seed),$random(seed)}; end
     5: begin w[7:0]=2; w[92:30]={$random(seed),$random(seed)}; w[91]=1; end
     6: begin w[7:0]=9; w[143:30]={$random(seed),$random(seed),$random(seed),$random(seed)}; end
     7: begin w[7:0]=4; w[88:30]=ua.result_word[88:30]; w[90:89]=ua.result_word[90:89]; end
     8: begin w[7:0]=8; w[88:30]=ua.accepted_tag; w[90:89]=ua.accepted_gen; end
     default: begin w[7:0]=3; end
    endcase
    if(($random(seed)&127)==0) w[300]=1;
    rx_valid[i]=1; rx_data[i*512+:512]=w;
   end
  end
  $display("HR_PEER_CODEC_PD seed=%0d cycles=%0d resets=%0d class6_sends=%0d rx_accepted=%0d mismatches=%0d first=%0d %s",
   SEED,NCYC,resets,sends6,rxacc,mism,first,(mism==0&&resets>=20&&sends6>=1000&&rxacc>=10000)?"PASS":"FAIL");
  $finish;
 end
endmodule
