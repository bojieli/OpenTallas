`timescale 1ns/1ps
// KV-MU7 10-20: the full multi-user HOST root mechanism, 4 users: packet -> scheduler -> package -> observer -> POST.
// Die 0 = the release HOST MU family as the KV die binds it (GEN9 d22bu, OT_KV_MU=1: qkd_host_root_admission_mu children):
//   PROMPT leaf  qkd_hr_core_prompt_mu4p3_n32 (the closing native32 leaf, KV-HOST9B 26aa2a496; +define+PROMPT_PS3 = its
//                RTL source qkd_hr_core_prompt_mu4_ps3) = u_axi (host packet ABI v1) + u_control (MU 1 control:
//                SQ/prompt DMA, 4-slot scheduler ot_host_if_pb2_observed ps3, ot_qfd_pkgctl MU 1 package controller,
//                CQ DMA, observer step/CQ faces with raw position + slot) + u_hc station;
//   PEER family  token service qkd_host_ctrl_token_service_packet_collected_mu (cmd -> hc, tk8/kst8/boot8 collection),
//                qkd_host_peer_root_mux, qkd_host_tp8_coordinator_mu #(POST_UID_SLOT 1) (allocator/cohort/codec/
//                lifecycle/POST collector _mu), rank-0 qkd_host_peer_rank_codec (the observer's step/CQ faces);
//   GUARD family qkd_host_native_token_endpoint_cancel_mu (4 contexts).
// Dies 1..7: token service _mu + rank codec + endpoint _mu each; their class9 rank traffic shares die 0's ONE physical
// root-mux port (bench link router), token-service frames go through a bench frame router (one frame / 2 edges / die).
// Die model (bench): KV layer programme _mu (4 contexts, 36 writer stages, row 64+l+256u) started at the user's frame
// slot on cohort dispatch; KV done -> engine result (token = the user's generated token for that position).
// Host (bench): packets only (BAR write/read 0x01/0x02 -> 0x81/0x82, DMA read 0x12 -> 0x13, DMA write 0x14 -> 0x15),
// credits both ways (RX_DEPTH 4 / TX_CRED 4); host RAM holds the SQ (4 requests), prompts and the CQ.
// Fixtures (declared, not part of this mechanism): service-epoch bootstrap (prompt sees service_ready 1 /
// service_ready8 ff / no begin credit, token services startup_allowed 1 and no begin), image/program loader
// (rank codecs program_ready 1, fixed epoch/digest; prompt program outputs open), service guard (endpoint local_tk goes
// straight to the token service), rx/tx link class mux + PHY (packets enter at the u_axi / token-service faces).
// Checks: every die start names its user (pos[17:16]), next position, right input token (prompt token, else the user's
// previous output); grant epoch {seq14[user],user2}; rank requests / dispatch / writer rows / retire reports carry the
// user's identity; every POST names its own terminal, after all 8 rank releases of that terminal, within POST_LIM of its
// KV done; CQ per user in order (slot/tag/pos/token/ngen/kind); counts exact; >=3 users in flight; no fault anywhere.
module tb_mu_hroot_full;
 reg ck=0;always #0.5 ck=~ck;
 reg por_n=0;
 integer cyc=0;always @(posedge ck)cyc<=cyc+1;
 localparam integer NU=4,POST_LIM=400;
 integer fails=0;reg trace=0;initial trace=$test$plusargs("TRACE");
 task fail(input[1023:0]m);begin fails=fails+1;if(fails<16)$display("ERR cyc %0d %0s",cyc,m);end endtask
 // per-user request (as tb_qkd_host_mu_out): prompt length, tokens to generate
 integer plen[0:NU-1],maxn[0:NU-1];
 initial begin plen[0]=2;plen[1]=3;plen[2]=1;plen[3]=4;maxn[0]=3;maxn[1]=2;maxn[2]=4;maxn[3]=3;end
 function automatic [17:0] ptok(input integer u,input integer i);ptok=18'(256*(u+1)+i+5);endfunction
 function automatic [17:0] otok(input integer u,input integer p);otok=18'(32'h20000+u*4096+p*5+3);endfunction
 function automatic [31:0] oval(input integer u,input integer p);oval=32'h3f800000+u*65536+p;endfunction

 // ======================= die 0 PROMPT leaf =======================
 wire host_rst_n,link_rst_n,hbm_rst_n,boot_go,die_rst_n,sys_ready,pr_irq,source_cr,available,service_faults;
 wire[31:0]fault_src;wire[142:0]pr_hc;wire package_abort;wire host_interface_idle;
 wire program_fault,ingress_fault,commit_fault,host_observer_fault,source_fault,begin_fault,startup_allowed;
 wire cq_commit_v;wire[15:0]cq_client_tag;wire[17:0]cq_pos,cq_token;wire[7:0]cq_slot;
 wire step_issue_v,step_retire_v,step_retire_cq;wire[15:0]step_client_tag,step_retire_client_tag;wire[17:0]step_pos,step_retire_pos,step_retire_token;wire[7:0]step_slot,step_retire_slot;
 wire cmd_v;wire[181:0]cmd_hc;wire cmd_cr;
 wire pr_begin_v;wire[15:0]pr_begin_epoch;
 reg hv=0;reg[511:0]hd=0;wire hr;wire ht;wire[511:0]htd;reg htc=0;
 wire pr_rx_v;wire[527:0]pr_rx_d;
 reg[1:0]link_up=0;
 wire[15:0]ts0_boot8;wire[79:0]ts0_kst8;wire[743:0]ts0_tk8;
 wire t_tev0;wire[15:0]t_te0;
 wire a_v,a_d;
 wire[7:0]owned;
 wire[7:0]rq_v;wire[471:0]rq_tag;wire[15:0]rq_gen;wire[143:0]rq_tok,rq_pos;
`ifdef PROMPT_PS3
 qkd_hr_core_prompt_mu4_ps3 pr(
`else
 qkd_hr_core_prompt_mu4p3_n32 pr(
`endif
  .ck_core(ck),.static_setup_ready(1'b1),.boot_pr(),.boot_image_target(),.boot_image_ready(),.boot_image_fault(),
  .program_epoch(),.program_digest(),.package_abort(package_abort),.token_epoch_valid(t_tev0),.token_epoch(t_te0),
  .service_abort(1'b0),.ingest_permission(1'b0),.service_diag_raw(26'd0),.service_status(32'd0),.die_id(3'd0),
  .link_up(link_up),.crom_fault(1'b0),.record_send_kind(2'd0),.record_witness_slot(1'b0),.record_rx_v(1'b0),
  .record_rx(548'd0),.record_tx_v(),.record_tx_observed_v(),.record_tx(),.record_fault(),.execution_active(1'b0),
  .program_ready(),.program_authorized_footer_v(),.program_authorized_footer64(),.program_begin_v(),.program_auth_v(),
  .program_expected_pw(),.program_expected_dw(),.program_auth_epoch(),.program_auth_digest(),.hc(pr_hc),.irq(pr_irq),
  .host_rst_n(host_rst_n),.link_rst_n(link_rst_n),.hbm_rst_n(hbm_rst_n),.boot_go(boot_go),.die_rst_n(die_rst_n),
  .sys_ready(sys_ready),.fault_src(fault_src),.source_cr(source_cr),.available(available),.service_faults(service_faults),
  .host_link_reset_req(1'b0),.host_interface_idle(host_interface_idle),.allocated_valid(a_v),
  .native_context_owned(owned[0]),.u_rank__u_control__por_n(por_n),.u_rank__u_control__service_ready(1'b1),
  .u_rank__program_fault(program_fault),.u_rank__ingress_fault(ingress_fault),.u_rank__commit_fault(commit_fault),
  .host_observer_fault(host_observer_fault),.u_rank__source_fault(source_fault),
  .cq_client_tag(cq_client_tag),.cq_commit_v(cq_commit_v),.cq_pos(cq_pos),.cq_slot(cq_slot),.cq_token(cq_token),
  .native_request_gen(rq_gen[1:0]),.native_request_pos(rq_pos[17:0]),.native_request_tag(rq_tag[58:0]),
  .native_request_token(rq_tok[17:0]),.native_request_v(rq_v[0]),
  .step_client_tag(step_client_tag),.step_issue_v(step_issue_v),.step_pos(step_pos),
  .step_retire_client_tag(step_retire_client_tag),.step_retire_cq(step_retire_cq),.step_retire_pos(step_retire_pos),
  .step_retire_slot(step_retire_slot),.step_retire_token(step_retire_token),.step_retire_v(step_retire_v),.step_slot(step_slot),
  .u_rank__u_control__begin_epoch(pr_begin_epoch),.u_rank__begin_fault(begin_fault),
  .u_rank__u_control__ctrl_begin_available(1'b0),.u_rank__u_control__begin_cr(1'b0),.u_rank__u_control__begin_v(pr_begin_v),
  .u_rank__u_control__boot8(ts0_boot8),.u_rank__u_control__kst8(ts0_kst8),.u_rank__peer_pending_ack(8'd0),
  .u_rank__guarded_physical(8'd0),.u_rank__peer_service_epoch(128'd0),.u_rank__peer_service_ready(8'hff),
  .u_rank__u_control__startup_allowed(startup_allowed),.u_rank__u_control__tk8(ts0_tk8),.u_rank__guarded_transport(8'd0),
  .u_rank__u_control__cmd_cr(cmd_cr),.u_rank__u_control__cmd_hc(cmd_hc),.u_rank__u_control__cmd_v(cmd_v),
  .u_rank__u_control__u_packet__hr(hr),.u_rank__u_control__u_packet__hd(hd),.u_rank__u_control__u_packet__hv(hv),
  .u_rank__u_control__u_packet__htc(htc),.u_rank__u_control__u_packet__htd(htd),.u_rank__u_control__u_packet__ht(ht),
  .u_rank__rx_cr(1'b0),.u_rank__rx_d(pr_rx_d),.u_rank__rx_v(pr_rx_v),
  .u_rank__program_rx_cr(),.u_rank__program_rx_d(528'd0),.u_rank__program_rx_v(1'b0));
 wire rst_n=host_rst_n;

 // ======================= token services (die 0 + 7 peers) =======================
 wire kac,drn;reg kst=0;
 reg ts_rx_v[0:7];reg[511:0]ts_rx_d[0:7];reg ts_tx_cr[0:7];
 wire ts_tx_v[0:7];wire[511:0]ts_tx_d[0:7];wire[181:0]ts_hc[0:7];wire ts_fault[0:7];wire ts_tev[0:7];wire[15:0]ts_te[0:7];
 wire ts_cv[0:7];wire[58:0]ts_ct[0:7];wire[1:0]ts_cg[0:7];wire ts_cd[0:7],ts_cf[0:7];wire[3:0]ts_cdr[0:7];
 wire ts_trv[0:7],ts_tgr[0:7],ts_ccr[0:7];wire[17:0]ts_trt[0:7],ts_trp[0:7];wire[1:0]ts_trg[0:7];
 wire[15:0]ts_boot8[0:7];wire[79:0]ts_kst8[0:7];wire[743:0]ts_tk8[0:7];
 wire t_req_r,t_gv;wire[15:0]t_gep;wire[17:0]t_gtok,t_gpos;wire[1:0]t_ggen;wire[58:0]t_gtag;
 wire co_idf,co_wl,co_rc;
 wire[7:0]rs_v,rs_done,rs_fault,rs_cr,crel,rel_v,ep_fault,rc_fault,c_acc,rq_cr;
 wire[471:0]rs_tag,rel_tag;wire[15:0]rs_gen,rel_gen;wire[255:0]rq_trace,rs_val,rs_cyc;wire[143:0]rs_tok;wire[31:0]rs_cause;
 wire[743:0]ltk;
 for(genvar d=0;d<8;d=d+1)begin:g_ts
  qkd_host_ctrl_token_service_packet_collected_mu #(.STRAPPED(1),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1),.MU(1))ts(
   .ck(ck),.rst_n(rst_n),.die_id(3'(d)),.rx_v(ts_rx_v[d]),.rx_d(ts_rx_d[d]),.rx_cr(),.tx_v(ts_tx_v[d]),.tx_d(ts_tx_d[d]),.tx_cr(ts_tx_cr[d]),
   .local_tk(ltk[d*93+:93]),.local_kst(10'd0),.local_boot(2'b11),.cmd_v(d==0?cmd_v:1'b0),.cmd_hc(d==0?cmd_hc:182'd0),.cmd_cr(ts_ccr[d]),
   .hc(ts_hc[d]),.tk8(ts_tk8[d]),.kst8(ts_kst8[d]),.boot8(ts_boot8[d]),.seen(),.fault(ts_fault[d]),.startup_allowed(1'b1),.local_service_ready(1'b1),
   .local_service_epoch(16'd0),.begin_v(1'b0),.begin_epoch(16'd0),.begin_cr(),.begin_available(),.service_begin_v(),
   .service_begin_epoch(),.pending_advertised(),.pending_epoch(),.service_ready8(),.pending_ack8(),.service_epoch8(),
   .ingest_permission(),.por_n(por_n),.token_wrap_fence_valid(d==0?co_rc:1'b0),.token_wrap_drained(d==0?co_rc:1'b0),
   .token_wrap_link_reset_seen(d==0?co_rc:1'b0),.token_wrap_retraining_done(d==0?co_rc:1'b0),
   .token_allocator_fault(d==0?co_idf:1'b0),.package_abort(d==0?package_abort:1'b0),.abort_drained(d==0?{4{drn}}:4'd0),
   .token_request_valid(ts_trv[d]),.token_request_ready(d==0?t_req_r:1'b0),.token_request_token(ts_trt[d]),.token_request_position(ts_trp[d]),
   .token_request_generation(ts_trg[d]),.token_grant_valid(d==0?t_gv:1'b0),.token_grant_ready(ts_tgr[d]),
   .token_grant_epoch(d==0?t_gep:16'd0),.token_grant_token(d==0?t_gtok:18'd0),.token_grant_position(d==0?t_gpos:18'd0),
   .token_grant_generation(d==0?t_ggen:2'd0),.token_grant_tag(d==0?t_gtag:59'd0),.allocated_valid(d==0?a_v:1'b0),
   .allocated_delivered(d==0?a_d:1'b0),.allocated_epoch(d==0?t_gep:16'd0),.allocated_token(d==0?t_gtok:18'd0),
   .allocated_position(d==0?t_gpos:18'd0),.allocated_generation(d==0?t_ggen:2'd0),.token_epoch_valid(ts_tev[d]),
   .token_epoch(ts_te[d]),.cancel_valid(ts_cv[d]),.cancel_tag(ts_ct[d]),.cancel_generation(ts_cg[d]),.cancel_done(ts_cd[d]),
   .cancel_fault(ts_cf[d]),.cancel_drained(ts_cdr[d]),.terminal_accepted(c_acc[d]));
 end
 assign cmd_cr=ts_ccr[0];assign ts0_boot8=ts_boot8[0];assign ts0_kst8=ts_kst8[0];assign ts0_tk8=ts_tk8[0];
 assign t_tev0=ts_tev[0];assign t_te0=ts_te[0];

 // ======================= coordinator (MU 1, POST_UID_SLOT 1) + root mux =======================
 wire dispatch_valid,dispatched,co_fault,post_pending,consensus;wire[58:0]cohort_tag;wire[1:0]cohort_gen;wire[7:0]acc_ranks;
 reg er_v=0;reg[58:0]er_tag=0;reg[1:0]er_gen=0;reg[17:0]er_tok=0;reg[31:0]er_val=0;wire er_cr;
 wire[7:0]co_rx_valid,co_rx_ready,co_tx_valid,co_tx_ready;wire[4095:0]co_rx_data,co_tx_data;
 wire lo_tx_valid,lo_tx_ready,lo_rx_valid,lo_rx_ready;wire[511:0]lo_tx_data,lo_rx_data;
 reg ph_rx_valid=0;reg[511:0]ph_rx_data=0;wire ph_rx_ready;wire ph_tx_valid;wire[511:0]ph_tx_data;reg ph_tx_ready=0;
 wire rm_fault;
 qkd_host_peer_root_mux rm(.ck(ck),.por_n(por_n),.physical_rx_valid(ph_rx_valid),.physical_rx_data(ph_rx_data),.physical_rx_ready(ph_rx_ready),
  .physical_tx_valid(ph_tx_valid),.physical_tx_data(ph_tx_data),.physical_tx_ready(ph_tx_ready),
  .local_tx_valid(lo_tx_valid),.local_tx_data(lo_tx_data),.local_tx_ready(lo_tx_ready),.local_rx_valid(lo_rx_valid),.local_rx_data(lo_rx_data),.local_rx_ready(lo_rx_ready),
  .coordinator_rx_valid(co_rx_valid),.coordinator_rx_data(co_rx_data),.coordinator_rx_ready(co_rx_ready),.coordinator_tx_valid(co_tx_valid),.coordinator_tx_data(co_tx_data),.coordinator_tx_ready(co_tx_ready),.fault(rm_fault));
 qkd_host_tp8_coordinator_mu #(.MU(1),.POST_UID_SLOT(1)) co(.ck_codec(ck),.ck_lifecycle(ck),.ck_post(ck),.por_n(por_n),
  .peer_rx_valid(co_rx_valid),.peer_rx_data(co_rx_data),.peer_rx_ready(co_rx_ready),.peer_tx_valid(co_tx_valid),.peer_tx_data(co_tx_data),.peer_tx_ready(co_tx_ready),
  .token_request_valid(ts_trv[0]),.token_request_token(ts_trt[0]),.token_request_position(ts_trp[0]),.token_request_gen(ts_trg[0]),.token_request_ready(t_req_r),
  .token_grant_valid(t_gv),.token_grant_ready(ts_tgr[0]),.token_grant_epoch(t_gep),.token_grant_token(t_gtok),.token_grant_position(t_gpos),.token_grant_gen(t_ggen),.token_grant_tag(t_gtag),
  .allocated_valid(a_v),.allocated_delivered(a_d),.engine_admit_ready(1'b1),.dispatch_valid(dispatch_valid),.dispatched(dispatched),.cohort_tag(cohort_tag),.cohort_gen(cohort_gen),
  .accepted_ranks(acc_ranks),.participant_trace(),.participant_token(),.participant_pos(),
  .engine_result_v(er_v),.engine_result_tag(er_tag),.engine_result_gen(er_gen),.engine_result_done(1'b1),.engine_result_fault(1'b0),.engine_result_cause(4'd0),
  .engine_result_token(er_tok),.engine_result_value(er_val),.engine_result_cycles(32'd77),.engine_result_cr(er_cr),
  .program_consensus(consensus),.program_epoch(),.program_digest(),.certificate_valid(),.certificate(),.certificate_prefix(),
  .wrap_locked(co_wl),.identity_fault(co_idf),.recovery_complete(co_rc),.post_pending(post_pending),.fault(co_fault));

 // ======================= 8 ranks: rank codec + endpoint _mu =======================
 reg cert_v=0;
 wire[7:0]rc_tx_valid,rc_rx_ready;wire[4095:0]rc_tx_data;reg[7:0]rc_tx_ready=0,rc_rx_valid=0;reg[511:0]rc_rx_data[0:7];
 initial for(integer k=0;k<8;k=k+1)rc_rx_data[k]=0;
 assign lo_tx_valid=rc_tx_valid[0];assign lo_tx_data=rc_tx_data[511:0];
 assign lo_rx_ready=rc_rx_ready[0];
 for(genvar d=0;d<8;d=d+1)begin:g_rk
  wire rc_txr=(d==0)?lo_tx_ready:rc_tx_ready[d];
  wire rc_rxv=(d==0)?lo_rx_valid:rc_rx_valid[d];
  wire[511:0]rc_rxd=(d==0)?lo_rx_data:rc_rx_data[d];
  wire[181:0]ep_hc=(d==0)?{pr_hc,ts_hc[0][38:0]}:ts_hc[d];
  qkd_host_peer_rank_codec #(.RANK(d))rc(.ck(ck),.por_n(por_n),.tx_valid(rc_tx_valid[d]),.tx_data(rc_tx_data[d*512+:512]),.tx_ready(rc_txr),.rx_valid(rc_rxv),.rx_data(rc_rxd),.rx_ready(rc_rx_ready[d]),
   .request_v(rq_v[d]),.request_tag(rq_tag[d*59+:59]),.request_gen(rq_gen[d*2+:2]),.request_trace(rq_trace[d*32+:32]),.request_token(rq_tok[d*18+:18]),.request_pos(rq_pos[d*18+:18]),.request_cr(rq_cr[d]),.request_aborted(),
   .cancel_valid(ts_cv[d]),.cancel_tag(ts_ct[d]),.cancel_gen(ts_cg[d]),.cancel_done(ts_cd[d]),.cancel_fault(ts_cf[d]),.cancel_drained(ts_cdr[d]),.cancel_accepted(c_acc[d]),
   .cancel_release_v(rel_v[d]),.cancel_release_tag(rel_tag[d*59+:59]),.cancel_release_gen(rel_gen[d*2+:2]),.cancel_released(crel[d]),
   .result_v(rs_v[d]),.result_tag(rs_tag[d*59+:59]),.result_gen(rs_gen[d*2+:2]),.result_done(rs_done[d]),.result_fault(rs_fault[d]),.result_cause(rs_cause[d*4+:4]),.result_token(rs_tok[d*18+:18]),.result_value(rs_val[d*32+:32]),.result_cycles(rs_cyc[d*32+:32]),.result_cr(rs_cr[d]),
   .service_ready(1'b1),.native_ready(1'b1),.service_epoch(16'd3),.drained({4{drn}}),.context_owned(owned[d]),.links_drained(1'b1),.link_reset_seen(1'b0),.retrained(1'b0),.program_ready(1'b1),.program_epoch(16'd7),.program_digest(64'h123456789abcdef),
   .step_issue_v(d==0&&step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.step_retire_v(d==0&&step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
   .cq_commit_v(d==0&&cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.certificate_v(cert_v),.certificate(66'h1234),.certificate_prefix(32'd0),
   .allocated_valid(),.allocated_delivered(),.allocated_epoch(),.allocated_token(),.allocated_position(),.allocated_gen(),.reset_request(),.retrain_request(),.recovery_clear(),.fault(rc_fault[d]));
  qkd_host_native_token_endpoint_cancel_mu #(.ENABLE_NATIVE(1),.MU(1))ep(.ck(ck),.por_n(por_n),.rst_n(rst_n),.hc(ep_hc),.legacy_tk(93'd0),.image_ready(1'b1),
   .shared_epoch_valid(ts_tev[d]),.shared_epoch(ts_te[d]),
   .request_v(rq_v[d]),.request_tag(rq_tag[d*59+:59]),.request_trace(rq_trace[d*32+:32]),.request_gen(rq_gen[d*2+:2]),.request_token(rq_tok[d*18+:18]),.request_pos(rq_pos[d*18+:18]),.request_cr(rq_cr[d]),.native_pr(),
   .result_v(rs_v[d]),.result_tag(rs_tag[d*59+:59]),.result_gen(rs_gen[d*2+:2]),.result_done(rs_done[d]),.result_fault(rs_fault[d]),.result_cause(rs_cause[d*4+:4]),.result_token(rs_tok[d*18+:18]),.result_value(rs_val[d*32+:32]),.result_cycles(rs_cyc[d*32+:32]),.result_cr(rs_cr[d]),
   .kv_drained(drn),.vm_drained(drn),.collective_drained(drn),.host_drained(drn),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(1'b0),
   .cancel_release_v(rel_v[d]),.cancel_release_tag(rel_tag[d*59+:59]),.cancel_release_gen(rel_gen[d*2+:2]),.context_owned(owned[d]),.cancel_released(crel[d]),.local_tk(ltk[d*93+:93]),.protocol_fault(ep_fault[d]));
 end

 // ======================= KV layer programme _mu + KV row (die model) =======================
 reg we=0;reg[8:0]ad=0;reg[63:0]da=0;reg[15:0]kep=0;reg[17:0]ktok=0,kpos=0;reg[1:0]kgen=0;
 wire cg,kg,vg,ai,ar,ws,ls,ss,sd,qq,cf,kdn,kft;wire[5:0]cs,kstg,klay;wire[15:0]kepo;wire[17:0]ktko,kpso;
 wire[13:0]kct;wire[1:0]kgno;wire[7:0]kfc;wire[31:0]kage,ktc;
 qkd_static_kv_layer_programme_mu #(.MU(1)) kv(
  .ck(ck),.rst_n(rst_n),.cfg_we(we),.cfg_addr(ad),.cfg_data(da),.start(kst),.authority_valid(1'b1),
  .programme_authorized(1'b1),.programme_epoch(16'h00a5),.programme_digest(64'hfeedfacecafebeef),.authority_epoch(kep),
  .authority_token(ktok),.authority_position(kpos),.authority_generation(kgen),.ctrl_go(cg),.kgo(kg),.vgo(vg),
  .attention_issue(ai),.attention_run(ar),.writer_start(ws),.link_start(ls),.stage_start(ss),.stage_done(sd),
  .expected_upstream_quiet(qq),.completed_stage(cs),.stage(kstg),.layer(klay),.epoch(kepo),.token(ktko),.position(kpso),
  .ctx_t(kct),.generation(kgno),.configured(cf),.active(kac),.done(kdn),.fault(kft),.fault_code(kfc),.age(kage),
  .token_cycles(ktc));
 assign drn=!kac&&!kst;
 wire[28:0]xa_o;wire rf;wire[287:0]es_o;
 qkd_kv_mu_wrow #(.MU(1),.NL(1)) wrow(.user(kepo[1:0]),.es_i(288'd0),.xa_i({19'(64+klay),10'd0}),.es_o(es_o),.xa_o(xa_o),.range_fault(rf));

 // ======================= token-service frame router (as tb_mu_peer_e2e) =======================
 reg[511:0]rq[0:7][0:63];integer rqw[0:7],rqr[0:7],rgap[0:7],crp[0:7];integer i,t,ri,fi,bi;
 initial for(i=0;i<8;i=i+1)begin rqw[i]=0;rqr[i]=0;rgap[i]=0;crp[i]=0;ts_rx_v[i]=0;ts_rx_d[i]=0;ts_tx_cr[i]=0;end
 always @(negedge ck)begin
  for(ri=0;ri<8;ri=ri+1)begin
   ts_rx_v[ri]=0;ts_tx_cr[ri]=0;
   if(ts_tx_v[ri])begin
    t=-1;for(integer b=0;b<8;b=b+1)if(ts_tx_d[ri][24+b])t=b;
    if(t<0||ts_tx_d[ri][31:24]!=(8'd1<<t))fail("frame router: frame without one target");
    else begin rq[t][rqw[t]%64]=ts_tx_d[ri];rqw[t]=rqw[t]+1;end
    crp[ri]=crp[ri]+1;
   end
  end
  for(ri=0;ri<8;ri=ri+1)begin
   if(crp[ri]>0)begin ts_tx_cr[ri]=1;crp[ri]=crp[ri]-1;end
   if(rgap[ri]>0)rgap[ri]=rgap[ri]-1;
   else if(rqr[ri]<rqw[ri])begin ts_rx_v[ri]=1;ts_rx_d[ri]=rq[ri][rqr[ri]%64];rqr[ri]=rqr[ri]+1;rgap[ri]=1;end
  end
 end

 // ======================= class9 link router: ranks 1..7 <-> die 0's single physical root-mux port =======================
 // upstream: rank codec tx (valid/ready) -> one ordered link FIFO -> root mux physical_rx; downstream: root mux
 // physical_tx -> per-rank FIFO (by destination [13:11]) -> rank codec rx.  Handshakes are sampled at posedge.
 reg[511:0]upq[0:255];integer upw=0,upr=0;reg[511:0]dnq[0:7][0:63];integer dnw[0:7],dnr[0:7];
 reg[7:0]up_hs=0,dn_hs=0;reg[511:0]up_cap[0:7];reg ph_rx_hs=0,ph_tx_hs=0;reg[511:0]ph_tx_cap=0;
 initial for(i=0;i<8;i=i+1)begin dnw[i]=0;dnr[i]=0;end
 always @(posedge ck)begin
  for(integer r=1;r<8;r=r+1)begin up_hs[r]<=rc_tx_valid[r]&&rc_tx_ready[r];up_cap[r]<=rc_tx_data[r*512+:512];dn_hs[r]<=rc_rx_valid[r]&&rc_rx_ready[r];end
  ph_rx_hs<=ph_rx_valid&&ph_rx_ready;ph_tx_hs<=ph_tx_valid&&ph_tx_ready;ph_tx_cap<=ph_tx_data;
 end
 always @(negedge ck)begin:link_router
  integer r,dst;
  for(r=1;r<8;r=r+1)if(up_hs[r])begin upq[upw%256]=up_cap[r];upw=upw+1;end
  if(ph_rx_hs)upr=upr+1;
  if(ph_tx_hs)begin dst=ph_tx_cap[13:11];if(dst<1)fail("link router: downstream to rank 0");else begin dnq[dst][dnw[dst]%64]=ph_tx_cap;dnw[dst]=dnw[dst]+1;end end
  for(r=1;r<8;r=r+1)if(dn_hs[r])dnr[r]=dnr[r]+1;
  ph_rx_valid=upr<upw;ph_rx_data=upq[upr%256];
  if(!por_n)begin upw=0;upr=0;for(r=1;r<8;r=r+1)begin dnw[r]=0;dnr[r]=0;end end   // the link is in reset with the dies
  for(r=1;r<8;r=r+1)begin rc_tx_ready[r]=por_n&&(upw-upr)<200;rc_rx_valid[r]=dnr[r]<dnw[r];rc_rx_data[r]=dnq[r][dnr[r]%64];end
  ph_rx_valid=upr<upw;
  ph_tx_ready=por_n;for(r=1;r<8;r=r+1)if(dnw[r]-dnr[r]>48)ph_tx_ready=0;
 end

 // ======================= host: packet ABI v1 over credits =======================
 reg[63:0]mem[0:2047];
 reg[511:0]hq[0:63];integer hqw=0,hqr=0,h_cred=4,cq_writes=0,dma_reads=0,bar_resp=0;
 reg[31:0]bar_rdata;reg[15:0]bar_id=16'h0100;reg bar_seen=0;
 reg ht_q=0,hr_q=0;reg[511:0]htd_q=0;always @(posedge ck)begin ht_q<=ht;htd_q<=htd;hr_q<=hr;end
 task automatic hsend(input[511:0]p);begin hq[hqw%64]=p;hqw=hqw+1;end endtask
 // host <-> leaf packets (one process: credits, DMA answers, BAR responses; one tx credit back per received packet)
 always @(negedge ck)begin:host_io
  reg[511:0]p;reg[511:0]q;reg[63:0]a;
  if(hr_q)h_cred=h_cred+1;                               // rx_cr pulse: the leaf consumed one packet
  hv=0;
  if(hqr<hqw&&h_cred>0)begin hv=1;hd=hq[hqr%64];hqr=hqr+1;h_cred=h_cred-1;end
  htc=0;
  if(ht_q)begin
   p=htd_q;htc=1;
   case(p[7:0])
    8'h81:begin bar_resp=bar_resp+1;bar_seen=1;if(p[31:16]!==bar_id)fail("BAR write response id");if(p[33:32]!=0)fail("BAR write error response");end
    8'h82:begin bar_resp=bar_resp+1;bar_seen=1;bar_rdata=p[127:96];if(p[31:16]!==bar_id)fail("BAR read response id");end
    8'h12:begin a=p[95:32];dma_reads=dma_reads+1;q=0;q[7:0]=8'h13;q[15:8]=8'd1;q[34]=1'b1;q[159:96]=mem[a[13:3]];hsend(q);end
    8'h14:begin a=p[95:32];if(p[167:160]!=8'hff)fail("DMA write strobe");mem[a[13:3]]=p[159:96];cq_writes=cq_writes+1;q=0;q[7:0]=8'h15;q[15:8]=8'd1;hsend(q);end
    default:begin fail("unknown packet from the leaf");$display("  op %h",p[7:0]);end
   endcase
  end
 end
 task automatic bar_wr(input[12:0]a,input[31:0]v);reg[511:0]p;integer n;begin
  bar_id=bar_id+1;bar_seen=0;p=0;p[7:0]=8'h01;p[15:8]=8'd1;p[31:16]=bar_id;p[44:32]=a;p[127:96]=v;p[131:128]=4'hf;hsend(p);
  n=0;while(!bar_seen&&n<4000)begin @(negedge ck);n=n+1;end
  if(!bar_seen)begin $display("FAIL MU_HROOT_FULL BAR write timeout %h",a);$finish;end
 end endtask
 task automatic bar_rd(input[12:0]a,output[31:0]v);reg[511:0]p;integer n;begin
  bar_id=bar_id+1;bar_seen=0;p=0;p[7:0]=8'h02;p[15:8]=8'd1;p[31:16]=bar_id;p[44:32]=a;hsend(p);
  n=0;while(!bar_seen&&n<4000)begin @(negedge ck);n=n+1;end
  if(!bar_seen)begin $display("FAIL MU_HROOT_FULL BAR read timeout %h",a);$finish;end
  v=bar_rdata;
 end endtask

 // ======================= per-user step identity bookkeeping =======================
 // A user has at most one step in flight (cmd -> pkgctl retire).  k = the user's step index.
 integer nxt[0:NU-1],busy[0:NU-1],k_cmd[0:NU-1],k_grant[0:NU-1],k_disp[0:NU-1],k_done[0:NU-1],k_post[0:NU-1],k_ret0[0:NU-1],k_obs[0:NU-1];
 reg[15:0]id_ep[0:NU-1][0:15];reg[17:0]id_tok[0:NU-1][0:15],id_pos[0:NU-1][0:15];reg[1:0]id_gen[0:NU-1][0:15];
 integer done_cyc[0:NU-1][0:15],cmd_cyc[0:NU-1][0:15],post_cyc[0:NU-1][0:15],kvbusy[0:NU-1],wr_of[0:NU-1];
 reg[35:0]layer_seen[0:NU-1];reg[5:0]last_layer[0:NU-1];reg[7:0]relmask[0:NU-1];
 integer starts=0,outstanding=0,max_out=0,nreq=0,nws=0,ndisp=0,npost=0,overlap_disp=0,overlap_post=0,maxlat=0,peer_starts=0,
         epoch_out_of_order=0,nrel=0,relchk=0,nobs_issue=0,nobs_retire=0,nobs_cq=0,nret0=0;
 reg[15:0]last_grant_ep=0;reg any_grant=0;integer last_gen=-1;
 initial for(i=0;i<NU;i=i+1)begin nxt[i]=0;busy[i]=0;k_cmd[i]=0;k_grant[i]=0;k_disp[i]=0;k_done[i]=0;k_post[i]=0;k_ret0[i]=0;k_obs[i]=0;
  kvbusy[i]=0;wr_of[i]=0;layer_seen[i]=0;last_layer[i]=0;relmask[i]=0;end
 function automatic integer others_busy(input integer u);integer k;begin others_busy=0;for(k=0;k<NU;k=k+1)if(k!=u&&kvbusy[k])others_busy=1;end endfunction
 // (1) package start leaving the leaf (pkgctl MU -> hc station -> cmd): user on pos[17:16], next position, input token
 always @(posedge ck)if(cmd_v&&cmd_hc[38])begin:cmd_mon
  integer u,p,k;u=cmd_hc[17:16];p=cmd_hc[15:0];k=k_cmd[u];
  if(busy[u])fail("user started twice (step outstanding)");
  if(p!=nxt[u])begin fail("start position != the user's next position");$display("  u%0d p%0d next %0d",u,p,nxt[u]);end
  if(cmd_hc[35:18]!==((p<plen[u])?ptok(u,p):otok(u,p-1)))begin fail("start input token");$display("  u%0d p%0d tok %h",u,p,cmd_hc[35:18]);end
  if(last_gen>=0&&cmd_hc[37:36]!==2'(last_gen+1))fail("package generation not +1 per start");
  last_gen=cmd_hc[37:36];
  id_tok[u][k]=cmd_hc[35:18];id_pos[u][k]=cmd_hc[17:0];id_gen[u][k]=cmd_hc[37:36];cmd_cyc[u][k]=cyc;k_cmd[u]=k+1;
  busy[u]=1;starts=starts+1;outstanding=outstanding+1;if(outstanding>max_out)max_out=outstanding;
  if(trace)$display("T %0d cmd u%0d p%0d k%0d gen %0d",cyc,u,p,k,cmd_hc[37:36]);
 end
 // (2) allocator grant: epoch {seq14[user], user2}, identity = the user's started step
 always @(posedge ck)if(t_gv&&ts_tgr[0])begin:grant_mon
  integer u,k;u=t_gep[1:0];k=k_grant[u];
  if(t_gpos[17:16]!==2'(u))fail("grant epoch user != position user");
  if(t_gep[15:2]!==14'(k))fail("allocator epoch != {seq14[user], user}");
  if(k>=k_cmd[u])fail("grant without a started step");
  else if(t_gtok!==id_tok[u][k]||t_gpos!==id_pos[u][k]||t_ggen!==id_gen[u][k])fail("grant identity != the started step");
  if(any_grant&&t_gep<last_grant_ep)epoch_out_of_order=epoch_out_of_order+1;
  any_grant=1;last_grant_ep=t_gep;id_ep[u][k]=t_gep;k_grant[u]=k+1;
  if(trace)$display("T %0d grant u%0d ep %h",cyc,u,t_gep);
 end
 function automatic [58:0] tagof(input integer u,input integer k,input integer st);
  tagof={id_ep[u][k],6'(st),id_tok[u][k],id_pos[u][k][12:0],6'd0};endfunction
 // (3) every die start carries the user's shared epoch
 always @(negedge ck)for(integer d=0;d<8;d=d+1)if(ts_hc[d][38])begin:start_mon
  integer u;u=ts_hc[d][17:16];
  if(!ts_tev[d]||ts_te[d][1:0]!==2'(u)||ts_te[d]!==((t_gv&&ts_tgr[0]&&t_gep[1:0]==2'(u))?t_gep:id_ep[u][k_grant[u]-1]))fail("die start without the user's shared epoch");
  if(d!=0)peer_starts=peer_starts+1;
 end
 // (4) rank requests: stripped position + the user's TAG
 always @(posedge ck)for(integer d=0;d<8;d=d+1)if(rq_v[d])begin:req_mon
  integer u,k;u=rq_tag[d*59+43+:2];k=k_grant[u]-1;nreq=nreq+1;
  if(rq_pos[d*18+:18]!=={5'd0,id_pos[u][k][12:0]})fail("request position not stripped");
  if(rq_tag[d*59+:59]!==tagof(u,k,0)||rq_gen[d*2+:2]!==id_gen[u][k])fail("request TAG/gen");
 end
 // (5) cohort dispatch -> the die model starts the user's KV token at its frame slot
 reg[1:0]kvq[0:63];integer kvqw=0,kvqr=0;
 always @(posedge ck)if(dispatch_valid)begin:disp_mon                  // dispatch_ready = engine_admit_ready = 1
  integer u,k;u=cohort_tag[44:43];k=k_disp[u];
  if(acc_ranks!==8'hff)fail("partial cohort dispatch");
  if(cohort_tag!==tagof(u,k,0)||cohort_gen!==id_gen[u][k])fail("cohort TAG/gen");
  if(others_busy(u))overlap_disp=overlap_disp+1;
  k_disp[u]=k+1;ndisp=ndisp+1;kvq[kvqw%64]=2'(u);kvqw=kvqw+1;
  if(trace)$display("T %0d dispatch u%0d k%0d",cyc,u,k);
 end
 always @(negedge ck)begin:kv_go
  integer u,k;kst=0;
  if(kvqr<kvqw&&rst_n)begin
   u=kvq[kvqr%64];k=k_disp[u]-1;
   if((cyc%64)==16*u)begin
    kst=1;kep=id_ep[u][k];ktok=id_tok[u][k];kpos={5'd0,id_pos[u][k][12:0]};kgen=id_gen[u][k];kvbusy[u]=1;wr_of[u]=0;layer_seen[u]=0;last_layer[u]=0;
    kvqr=kvqr+1;
   end
  end
 end
 // (6) writer stages
 always @(negedge ck)if(rst_n&&ws)begin:ws_mon
  integer u;u=kepo[1:0];nws=nws+1;
  if(kepo!==id_ep[u][k_disp[u]-1])fail("writer epoch is not the user's allocated epoch");
  if(xa_o[28:10]!==19'(64+klay+256*u))fail("KV row != 64+layer+256*user");
  if(rf)fail("row range fault");
  if(layer_seen[u][klay])fail("layer written twice for a user in one token");
  layer_seen[u][klay]=1;wr_of[u]=wr_of[u]+1;
  if(klay!=0&&klay!=last_layer[u]+1)fail("user layers out of order");
  last_layer[u]=klay;
 end
 // (7) KV done -> engine result: the user's generated token for that position
 reg[1:0]resq[0:63];integer resw=0,resr=0,er_busy=0;
 always @(posedge ck)if(kdn)begin:kdone_mon
  integer u,k;u=kepo[1:0];k=k_done[u];
  if(wr_of[u]!=36)fail("user token without 36 writer stages");
  kvbusy[u]=0;done_cyc[u][k]=cyc;k_done[u]=k+1;resq[resw%64]=2'(u);resw=resw+1;
  if(trace)$display("T %0d kvdone u%0d k%0d",cyc,u,k);
 end
 always @(negedge ck)begin
  er_v=0;
  if(er_cr)er_busy=0;
  if(!er_busy&&resr<resw&&rst_n)begin:er_send
   integer u,k,p;u=resq[resr%64];k=k_done[u]-1;p=id_pos[u][k][15:0];resr=resr+1;er_busy=1;
   er_v=1;er_tag=tagof(u,k,37);er_gen=id_gen[u][k];er_tok=otok(u,p);er_val=oval(u,p);
  end
 end
 // (8) die-0 endpoint retire report (the tk word the package controller collects)
 reg[92:0]ltk0_q=0;
 always @(posedge ck)begin
  ltk0_q<=ltk[92:0];
  if(rst_n&&ltk[92]&&ltk[91:90]!==ltk0_q[91:90])begin:ret_mon
   integer u,k,p;u=-1;
   for(integer x=0;x<NU;x=x+1)if(k_ret0[x]<k_done[x]&&ltk[81:64]===otok(x,id_pos[x][k_ret0[x]][15:0]))u=x;
   if(u<0)fail("retire report names no done step");
   else begin k=k_ret0[u];p=id_pos[u][k][15:0];k_ret0[u]=k+1;nret0=nret0+1;
    if(ltk[91:90]!==id_gen[u][k])fail("retire report generation");
    if(ltk[63:32]!==oval(u,p))fail("retire report value");
   end
  end
 end
 // (9) observer faces (raw position < 8192 + the scheduler slot)
 always @(posedge ck)if(rst_n)begin:obs_mon
  if(step_issue_v)begin nobs_issue=nobs_issue+1;if(step_slot>=NU||step_pos>=8192)fail("observer issue face: slot/raw position");end
  if(step_retire_v)begin:sr
   integer u;u=step_retire_slot;nobs_retire=nobs_retire+1;
   if(u>=NU)fail("observer retire slot");
   else begin
    if(!busy[u]||step_retire_pos!=nxt[u]||step_retire_token!==otok(u,nxt[u]))begin fail("observer retire: position/token");$display("  u%0d pos %0d/%0d tok %h",u,step_retire_pos,nxt[u],step_retire_token);end
    busy[u]=0;nxt[u]=nxt[u]+1;outstanding=outstanding-1;
   end
  end
  if(cq_commit_v)begin nobs_cq=nobs_cq+1;if(cq_slot>=NU||cq_pos>=8192)fail("observer CQ face: slot/raw position");end
 end
 // (10) rank release identity -> POST release check (as tb_mu_peer_e2e, KV-MU6)
 reg[58:0]rlast[0:7];reg[7:0]rlast_v=0;
 always @(posedge ck)if(rst_n)begin:rel_mon
  integer d,ru;
  for(d=0;d<8;d=d+1)begin
   if(crel[d]&&rlast_v[d])begin ru=rlast[d][44:43];rlast_v[d]=0;nrel=nrel+1;
    if(rlast[d][58:43]===id_ep[ru][k_post[ru]])relmask[ru][d]=1'b1;else fail("rank release names no current user epoch");end
   if(rel_v[d])begin rlast[d]=rel_tag[d*59+:59];rlast_v[d]=1'b1;end
  end
 end
 // (11) POST: own terminal, after its 8 releases, within POST_LIM of its KV done, in order per user
 always @(posedge ck)if(co.g_mu.u_lifecycle.post_retired)begin:post_mon
  integer u,k,lat;u=co.g_mu.u_lifecycle.post_tag[44:43];k=k_post[u];
  if(k>=k_done[u])fail("POST before the step's KV done");
  else if(co.g_mu.u_lifecycle.post_tag!==tagof(u,k,37))fail("POST identity");
  relchk=relchk+1;if(relmask[u]!==8'hff)begin fail("POST before all 8 rank releases of its own terminal");$display("  u%0d relmask %b",u,relmask[u]);end
  relmask[u]=0;
  lat=cyc-done_cyc[u][k];if(lat>maxlat)maxlat=lat;
  if(lat>POST_LIM)begin fail("POST late (waited for a global die drain while other users in flight)");$display("  u%0d lat %0d",u,lat);end
  if(others_busy(u))overlap_post=overlap_post+1;
  post_cyc[u][k]=cyc;k_post[u]=k+1;npost=npost+1;
  if(trace)$display("T %0d post u%0d k%0d lat %0d",cyc,u,k,lat);
 end
 // trace: coordinator link frames and the first coordinator sub-fault edges
 reg cf_q=0,pf_q=0;
 always @(posedge ck)begin
  cf_q<=co.g_mu.codec_fault;pf_q<=co.g_mu.post_fault;
  if(co.g_mu.codec_fault&&!cf_q)$display("T %0d codec_fault rises",cyc);
  if(co.g_mu.post_fault&&!pf_q)$display("T %0d post_fault rises",cyc);
  if(trace)for(integer x=0;x<8;x=x+1)begin
   if(co_rx_valid[x]&&co_rx_ready[x])$display("T %0d co<-r%0d op %0d src %0d dst %0d seq %0d",cyc,x,co_rx_data[x*512+:8],co_rx_data[x*512+8+:3],co_rx_data[x*512+11+:3],co_rx_data[x*512+14+:16]);
   if(co_tx_valid[x]&&co_tx_ready[x])$display("T %0d co->r%0d op %0d seq %0d",cyc,x,co_tx_data[x*512+:8],co_tx_data[x*512+14+:16]);
  end
 end
 // trace: observer faces at the leaf and the POST collector's inputs
 always @(posedge ck)if(trace&&rst_n)begin:pc_trace
  if(step_issue_v)$display("T %0d leaf step_issue slot %0d pos %0d",cyc,step_slot,step_pos);
  if(step_retire_v)$display("T %0d leaf step_retire slot %0d pos %0d cq %b",cyc,step_retire_slot,step_retire_pos,step_retire_cq);
  if(cq_commit_v)$display("T %0d leaf cq slot %0d pos %0d",cyc,cq_slot,cq_pos);
  if(co.g_mu.u_lifecycle.g_mu.u_post.step_issue_v)$display("T %0d PC step_issue slot %0d issued %b owned %b",cyc,co.g_mu.u_lifecycle.g_mu.u_post.step_slot,co.g_mu.u_lifecycle.g_mu.u_post.g_mu.issued,co.g_mu.u_lifecycle.g_mu.u_post.g_mu.owned);
  if(co.g_mu.u_lifecycle.g_mu.u_post.step_retire_v)$display("T %0d PC step_retire slot %0d retired %b",cyc,co.g_mu.u_lifecycle.g_mu.u_post.step_retire_slot,co.g_mu.u_lifecycle.g_mu.u_post.g_mu.retired);
  if(co.g_mu.u_lifecycle.g_mu.u_post.cq_commit_v)$display("T %0d PC cq slot %0d",cyc,co.g_mu.u_lifecycle.g_mu.u_post.cq_slot);
  if(co.g_mu.u_lifecycle.g_mu.u_post.terminal_accepted)$display("T %0d PC terminal u%0d",cyc,co.g_mu.u_lifecycle.g_mu.u_post.terminal_tag[44:43]);
  if(co.g_mu.u_lifecycle.g_mu.u_post.g_mu.new_alloc)$display("T %0d PC new_alloc u%0d owned %b",cyc,co.g_mu.u_lifecycle.g_mu.u_post.allocated_tag[44:43],co.g_mu.u_lifecycle.g_mu.u_post.g_mu.owned);
  if(co.g_mu.u_lifecycle.g_mu.u_post.g_mu.post_go)$display("T %0d PC post_go u%0d",cyc,co.g_mu.u_lifecycle.g_mu.u_post.g_mu.h);
 end
 // (12) faults
 always @(negedge ck)if(por_n&&rst_n&&sys_ready)begin
  for(fi=0;fi<8;fi=fi+1)if(ts_fault[fi])begin fail("token service fault");$display("  die %0d",fi);end
  if(co_fault)begin fail("coordinator fault");$display("  codec %b post %b identity %b lifecycle %b alloc %b cohort %b",co.g_mu.codec_fault,co.g_mu.post_fault,co.identity_fault,co.g_mu.lifecycle_fault,co.g_mu.u_lifecycle.g_mu.u_lifecycle.g_mu.allocator_fault,co.g_mu.u_lifecycle.g_mu.u_lifecycle.g_mu.cohort_fault);end
  if(co_idf)fail("coordinator identity_fault");
  if(|rc_fault)begin fail("rank codec fault");$display("  ranks %b",rc_fault);end
  if(rm_fault)fail("root mux fault");
  if(|ep_fault)fail("endpoint protocol_fault");
  if(kft)begin fail("KV programme fault");$display("  code %h cf %b",kfc,cf);end
  if(host_observer_fault)fail("observer fault");
  if(package_abort)fail("package abort");
  if(program_fault||ingress_fault||commit_fault||source_fault||begin_fault)begin fail("prompt leaf fault");$display("  prog %b ingress %b commit %b source %b begin %b",program_fault,ingress_fault,commit_fault,source_fault,begin_fault);end
  if(fails>=6)begin $display("FAIL MU_HROOT_FULL fails=%0d (stopped)",fails);$finish;end
 end

 // ======================= sequence =======================
 integer n,e,nent,steps_exp,ent_seen[0:NU-1],u,p;reg[31:0]v;reg[63:0]w0,w1;reg[17:0]tk;
 initial begin
  for(i=0;i<2048;i=i+1)mem[i]=0;
  for(u=0;u<NU;u=u+1)ent_seen[u]=0;
  repeat(8)@(negedge ck);por_n=1;repeat(12)@(negedge ck);link_up=2'b11;
  n=0;while(!sys_ready&&n<5000)begin @(negedge ck);n=n+1;end
  if(!sys_ready)begin $display("FAIL MU_HROOT_FULL boot: sys_ready never (host_rst_n %b die_rst_n %b boot8 %h)",host_rst_n,die_rst_n,ts0_boot8);$finish;end
  if(trace)$display("T %0d sys_ready",cyc);
  // KV programme boot: stage_end 64, roots 3..11, GAP 0 except user 3 before stage 5 (+64)
  for(bi=0;bi<36;bi=bi+1)begin
   @(negedge ck);we=1;ad=9*bi+0;da=3;@(negedge ck);ad=9*bi+1;da=4;@(negedge ck);ad=9*bi+2;da=5;@(negedge ck);ad=9*bi+3;da=6;
   @(negedge ck);ad=9*bi+4;da=10;@(negedge ck);ad=9*bi+5;da=7;@(negedge ck);ad=9*bi+6;da=8;@(negedge ck);ad=9*bi+7;da=11;
   @(negedge ck);ad=9*bi+8;da=64;
  end
  @(negedge ck);ad=324;da=64'hfeedfacecafebeef;@(negedge ck);ad=325;da=64'h00a5;
  for(bi=0;bi<144;bi=bi+1)begin @(negedge ck);ad=326+bi;da=(bi==3*36+4)?64:0;end
  @(negedge ck);ad=470;da=64'h514b564c59523336;@(negedge ck);we=0;
  repeat(4)@(negedge ck);
  if(!cf||kft)begin $display("FAIL MU_HROOT_FULL KV boot cf=%b fault=%b",cf,kft);$finish;end
  @(negedge ck);cert_v=1;@(negedge ck);cert_v=0;
  bi=0;while(!consensus&&bi<4000)begin @(negedge ck);bi=bi+1;end
  if(!consensus)fail("no program consensus");
  bar_rd(13'h0004,v);$display("CAPS %h",v);
  // host RAM: SQ at 0x100 (32 B entries), prompts at 0x400 + 0x40*u, CQ at 0x800 (16 B entries)
  for(u=0;u<NU;u=u+1)begin
   mem[32+4*u]  ={16'(maxn[u]),16'(plen[u]),16'(16'hA0+u),8'h01,8'h01};
   mem[32+4*u+1]=64'(32'h400+32'h40*u);
   mem[32+4*u+2]=64'(u);
   mem[32+4*u+3]=64'h0003ffff_0003ffff;
   for(i=0;i<plen[u];i=i+1)
    if(i%2==0)mem[128+8*u+i/2][31:0]=32'(ptok(u,i));else mem[128+8*u+i/2][63:32]=32'(ptok(u,i));
  end
  bar_wr(13'h010,32'h100);bar_wr(13'h014,0);bar_wr(13'h018,3);bar_wr(13'h024,32'h800);bar_wr(13'h028,0);bar_wr(13'h02c,5);bar_wr(13'h008,1);
  // users 0..2 arrive first (SQ tail 3); user 3 arrives after 6 POSTs (tail 4): its epoch {seq 0, user 3} then reaches
  // the peers after higher epochs of the other users (per-user epochs out of global order)
  bar_wr(13'h01c,3);
  n=0;while(npost<6&&n<100000)begin @(negedge ck);n=n+1;end
  bar_wr(13'h01c,4);
  nent=0;steps_exp=0;for(u=0;u<NU;u=u+1)begin nent=nent+maxn[u];steps_exp=steps_exp+plen[u]+maxn[u]-1;end
  n=0;while((cq_writes<2*nent||npost<steps_exp)&&n<400000)begin @(negedge ck);n=n+1;end
  repeat(100)@(negedge ck);
  if(cq_writes!=2*nent||starts!=steps_exp||nobs_retire!=steps_exp||outstanding!=0)begin
   fail("counts");$display("  cq_writes %0d/%0d starts %0d observer retires %0d / %0d outstanding %0d",cq_writes,2*nent,starts,nobs_retire,steps_exp,outstanding);end
  if(ndisp!=steps_exp||npost!=steps_exp||nret0!=steps_exp)begin fail("pipeline counts");$display("  dispatch %0d posts %0d die0 retires %0d / %0d",ndisp,npost,nret0,steps_exp);end
  if(nreq!=8*steps_exp)begin fail("rank request count");$display("  %0d",nreq);end
  if(nws!=36*steps_exp)begin fail("writer stage count");$display("  %0d",nws);end
  if(peer_starts!=7*steps_exp)begin fail("peer start count");$display("  %0d",peer_starts);end
  if(nobs_issue!=steps_exp)begin fail("observer issue count");$display("  %0d",nobs_issue);end
  if(nobs_cq!=nent)begin fail("observer CQ count");$display("  %0d/%0d",nobs_cq,nent);end
  if(max_out<3)begin fail("fewer than 3 users in flight");$display("  max %0d",max_out);end
  if(overlap_post<NU)begin fail("POSTs not overlapped with other users' KV work");$display("  %0d",overlap_post);end
  if(epoch_out_of_order==0)fail("bench lost its out-of-order epoch case");
  if(post_pending||(|owned)||a_v)fail("allocations/contexts/POSTs left at the end");
  for(e=0;e<nent;e=e+1)begin
   w0=mem[256+2*e];w1=mem[256+2*e+1];u=w0[15:8];
   if(u>=NU)begin fail("CQ slot");$display("  entry %0d slot %0d",e,u);end
   else begin
    p=plen[u]-1+ent_seen[u];tk={w1[49:48],w0[63:48]};
    if(w0[31:16]!==16'(16'hA0+u)||w0[47:32]!==16'(p)||tk!==otok(u,p)||w1[47:32]!==16'(ent_seen[u]+1)||
       w0[2:1]!==((ent_seen[u]==maxn[u]-1)?2'd2:2'd1)||w0[7:4]!==((ent_seen[u]==maxn[u]-1)?4'd2:4'd0)||w0[0]!==1'b1)begin
     fail("CQ entry");$display("  entry %0d w0 %h w1 %h user %0d expect pos %0d token %h",e,w0,w1,u,p,otok(u,p));end
    ent_seen[u]=ent_seen[u]+1;
   end
  end
  for(u=0;u<NU;u=u+1)if(ent_seen[u]!=maxn[u])begin fail("CQ entries per user");$display("  u%0d %0d/%0d",u,ent_seen[u],maxn[u]);end
  bar_rd(13'h00c,v);if(v[1])begin fail("STATUS fault");$display("  STATUS %h",v);end
  // measured: first cmd -> last POST, and per step cmd -> POST
  begin:meas
   integer s,kk,mx,sum,first,last;mx=0;sum=0;first=1<<30;last=0;
   for(u=0;u<NU;u=u+1)for(kk=0;kk<k_post[u];kk=kk+1)begin s=post_cyc[u][kk]-cmd_cyc[u][kk];sum=sum+s;if(s>mx)mx=s;
    if(cmd_cyc[u][kk]<first)first=cmd_cyc[u][kk];if(post_cyc[u][kk]>last)last=post_cyc[u][kk];end
   if(fails==0)
`ifdef PROMPT_PS3
    $display("PASS MU_HROOT_FULL prompt=ps3_rtl users=4 steps=%0d cq_entries=%0d posts=%0d release_checked=%0d rank_releases=%0d rank_requests=%0d peer_starts=%0d writer_stages=%0d max_users_in_flight=%0d overlap_dispatch=%0d overlap_post=%0d epochs_out_of_global_order=%0d max_post_after_kv_done=%0d step_cmd_to_post_avg=%0d max=%0d span_first_cmd_to_last_post=%0d dma_reads=%0d cycles=%0d",
`else
    $display("PASS MU_HROOT_FULL prompt=n32 users=4 steps=%0d cq_entries=%0d posts=%0d release_checked=%0d rank_releases=%0d rank_requests=%0d peer_starts=%0d writer_stages=%0d max_users_in_flight=%0d overlap_dispatch=%0d overlap_post=%0d epochs_out_of_global_order=%0d max_post_after_kv_done=%0d step_cmd_to_post_avg=%0d max=%0d span_first_cmd_to_last_post=%0d dma_reads=%0d cycles=%0d",
`endif
     starts,nent,npost,relchk,nrel,nreq,peer_starts,nws,max_out,overlap_disp,overlap_post,epoch_out_of_order,maxlat,sum/(npost>0?npost:1),mx,last-first,dma_reads,cyc);
   else $display("FAIL MU_HROOT_FULL fails=%0d starts=%0d posts=%0d cq_writes=%0d",fails,starts,npost,cq_writes);
  end
  $finish;
 end
 initial begin #2000000;$display("FAIL MU_HROOT_FULL timeout starts=%0d posts=%0d cq_writes=%0d fails=%0d",starts,npost,cq_writes,fails);$finish;end
endmodule
