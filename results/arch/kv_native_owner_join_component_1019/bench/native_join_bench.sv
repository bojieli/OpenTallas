`timescale 1ns/1ps
// External-interface component bench. No hierarchical force, deposit or setup.
module native_join_bench #(parameter integer FIXTURE_WDOG=(1 << 22));
 localparam integer H=512, RESPONSE_DEADLINE=384;
 // All component clock ports deliberately share clk. FUNCTIONAL_ONLY.

  reg clk=0; always #5 clk=~clk;
  reg rst_n=0,raw_por_n=0,warm_rst_n=0,pll_locked_i=0;
  reg health_bad_i=0,health_armed_i=0,health_cutoff_i=0;
  reg execution_restart_i=0,role_fault_i=0,owner_drained_i=0;
  wire[79:0] rc_identity;

  wire[79:0]health_identity_i=0;
  wire rc_bad,rc_armed,rc_retained_owned,rc_poison,rc_failure_pending,rc_report_once;
  wire[17:0]rc_mirror_pos,rc_mirror_tok,rc_mirror_ngen;
  wire[1:0]rc_mirror_state;
  wire rc_word0_offer,rc_response_confirmed;
  wire s_awvalid,s_wvalid,s_bready,s_arvalid,s_rready;
  wire[12:0]s_awaddr,s_araddr;wire[31:0]s_wdata;wire[3:0]s_wstrb;
  wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;wire[31:0]s_rdata;wire[1:0]s_bresp,s_rresp;
  wire m_arvalid,m_rready,m_awvalid,m_wvalid,m_bready,m_wlast;
  wire[63:0]m_araddr,m_awaddr,m_wdata;wire[7:0]m_arlen,m_awlen,m_wstrb;wire[2:0]m_arsize,m_awsize;
  wire m_arready,m_rvalid,m_rlast,m_awready,m_wready,m_bvalid;
  wire[63:0]m_rdata;wire[1:0]m_rresp,m_bresp;
  wire irq,pb_we,pb_re;wire[13:0]pb_waddr,pb_raddr;wire[17:0]pb_wdata;wire[17:0]pb_q;
  wire eng_start,eng_slot,eng_clr_req;wire[17:0]eng_token,eng_pos;wire[23:0]kv_base;
  wire eng_done,eng_fault;wire eng_clr_ack=0;wire[17:0]eng_next_token;wire[31:0]eng_cycles;
  wire arr_rst_n;wire[7:0]cfg_users;wire[17:0]cfg_prompt_len,cfg_gen_len;
  wire cq_commit_v;wire[15:0]cq_client_tag;wire[7:0]cq_slot;wire[17:0]cq_pos,cq_token;wire[1:0]cq_kind;wire[3:0]cq_status;
  wire step_issue_v,step_retire_v,step_retire_cq;wire[15:0]step_client_tag,step_retire_client_tag;
  wire[7:0]step_slot,step_retire_slot;wire[17:0]step_pos,step_retire_pos,step_retire_token;wire host_idle,host_observer_fault;
 wire cq_dma_retired_v,raw_done_unready;
 wire mon_aw_ack,mon_w_ack,mon_aw_source_valid,mon_w_source_valid;
 wire step_retire_native_valid,cq_native_valid_observed;
 wire  native_issue_ready;
 wire  native_cq_offer_ok;
 wire  native_cq_prospective_v,native_cq_prospective_native_valid;
 wire [86:0] native_cq_prospective_key;
 wire  native_bound_valid;
 wire [58:0] native_bound_tag;
 wire [1:0] native_bound_gen,native_bound_descgen;
 wire [15:0] native_bound_client;
 wire [7:0] native_bound_slot;
 wire [17:0] native_bound_pos;
 wire  native_join_fault;
 wire  health_native_valid;
 wire [58:0] health_native_tag;
 wire [1:0] health_native_gen;
 wire  issue_fire_v;
 wire [17:0] issue_token,issue_pos;
 wire [15:0] issue_client;
 wire [7:0] issue_slot;
 wire [1:0] issue_descgen;
 wire  event_insert_v,event_native_valid;
 wire [58:0] event_native_tag;
 wire [1:0] event_native_gen,event_descgen;
 wire  cq_offer_v,cq_native_valid;
 wire [58:0] cq_native_tag;
 wire [1:0] cq_native_gen,cq_descgen;
 wire  raw_done_v,raw_done_native_valid,raw_done_report_needed,native_certificate_v;
 wire [58:0] raw_done_tag;
 wire [1:0] raw_done_gen,raw_done_descgen;
 wire [15:0] raw_done_client;
 wire [7:0] raw_done_slot;
 wire [17:0] raw_done_pos;
 wire [58:0] native_certificate_tag;
 wire [1:0] native_certificate_gen,native_certificate_descgen;
 wire [15:0] native_certificate_client;
 wire [7:0] native_certificate_slot;
 wire [15:0] event_client,cq_offer_client,report_drained_client;
 wire [7:0] event_slot,cq_offer_slot,report_drained_slot;
 wire  report_drained_v,report_drained_cq,report_drained_native_valid;
 wire [58:0] report_drained_tag;
 wire [1:0] report_drained_gen,report_drained_descgen;
  qkd_host_if_pins_observed_rc #(.ENABLE_RETAINED_COMMIT(1),.ENABLE_NATIVE_OWNER_JOIN(1),.PB_READ_PIPE(5),.PB_VALID_ONLY(1),.HEALTH_CUTOFF_EDGES(H),.STEP_RESPONSE_DEADLINE_EDGES(RESPONSE_DEADLINE),.COMPONENT_FIXTURE(1),
    .NSLOT(1),.ENG_CTX(1),.MODE(0),.MU_OUT(0),.NW(18),.PLB(13),.CTX_MAX(8192),.FMT(1)) dut (
    .eng_start_unready(ctl_res[86]),.raw_done_unready(raw_done_unready),.cq_dma_retired_v(cq_dma_retired_v),.mon_aw_ack(mon_aw_ack),.mon_w_ack(mon_w_ack),.mon_aw_source_valid(mon_aw_source_valid),.mon_w_source_valid(mon_w_source_valid),.step_retire_native_valid(step_retire_native_valid),.cq_native_valid_observed(cq_native_valid_observed),.die_id(3'd0),.native_issue_ready(native_issue_ready),.native_cq_offer_ok(native_cq_offer_ok),.native_cq_prospective_v(native_cq_prospective_v),.native_cq_prospective_native_valid(native_cq_prospective_native_valid),.native_cq_prospective_key(native_cq_prospective_key),.native_bound_valid(native_bound_valid),.native_bound_tag(native_bound_tag),.native_bound_gen(native_bound_gen),.native_bound_descgen(native_bound_descgen),.native_bound_client(native_bound_client),.native_bound_slot(native_bound_slot),.native_bound_pos(native_bound_pos),.native_join_fault(native_join_fault),.health_native_valid(health_native_valid),.health_native_tag(health_native_tag),.health_native_gen(health_native_gen),.issue_fire_v(issue_fire_v),.issue_token(issue_token),.issue_pos(issue_pos),.issue_client(issue_client),.issue_slot(issue_slot),.issue_descgen(issue_descgen),.event_insert_v(event_insert_v),.event_native_valid(event_native_valid),.event_native_tag(event_native_tag),.event_native_gen(event_native_gen),.event_descgen(event_descgen),.cq_offer_v(cq_offer_v),.cq_native_valid(cq_native_valid),.cq_native_tag(cq_native_tag),.cq_native_gen(cq_native_gen),.cq_descgen(cq_descgen),.raw_done_v(raw_done_v),.raw_done_native_valid(raw_done_native_valid),.raw_done_report_needed(raw_done_report_needed),.native_certificate_v(native_certificate_v),.raw_done_tag(raw_done_tag),.raw_done_gen(raw_done_gen),.raw_done_descgen(raw_done_descgen),.raw_done_client(raw_done_client),.raw_done_slot(raw_done_slot),.raw_done_pos(raw_done_pos),.native_certificate_tag(native_certificate_tag),.native_certificate_gen(native_certificate_gen),.native_certificate_descgen(native_certificate_descgen),.native_certificate_client(native_certificate_client),.native_certificate_slot(native_certificate_slot),.event_client(event_client),.cq_offer_client(cq_offer_client),.report_drained_client(report_drained_client),.event_slot(event_slot),.cq_offer_slot(cq_offer_slot),.report_drained_slot(report_drained_slot),.report_drained_v(report_drained_v),.report_drained_cq(report_drained_cq),.report_drained_native_valid(report_drained_native_valid),.report_drained_tag(report_drained_tag),.report_drained_gen(report_drained_gen),.report_drained_descgen(report_drained_descgen),
    .clk(clk),.rst_n(rst_n),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),
    .health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.health_identity_i(health_identity_i),.health_cutoff_i(health_cutoff_i),
    .execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.owner_drained_i(owner_drained_i),
    .rc_bad(rc_bad),.rc_armed(rc_armed),.rc_retained_owned(rc_retained_owned),.rc_poison(rc_poison),.rc_failure_pending(rc_failure_pending),.rc_report_once(rc_report_once),
    .rc_mirror_pos(rc_mirror_pos),.rc_mirror_tok(rc_mirror_tok),.rc_mirror_ngen(rc_mirror_ngen),.rc_mirror_state(rc_mirror_state),.rc_identity(rc_identity),.rc_word0_offer(rc_word0_offer),.rc_response_confirmed(rc_response_confirmed),
    .s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr[11:0]),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),
    .s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr[11:0]),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),
    .m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_arlen(m_arlen),.m_arsize(m_arsize),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),
    .m_awvalid(m_awvalid),.m_awready(m_awready),.m_awaddr(m_awaddr),.m_awlen(m_awlen),.m_awsize(m_awsize),.m_wvalid(m_wvalid),.m_wready(m_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wlast(m_wlast),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp),
    .irq(irq),.pb_we(pb_we),.pb_waddr(pb_waddr),.pb_wdata(pb_wdata),.pb_re(pb_re),.pb_raddr(pb_raddr),.pb_q(pb_q),
    .eng_start(eng_start),.eng_token(eng_token),.eng_pos(eng_pos),.eng_slot(eng_slot),.kv_base(kv_base),.eng_done(eng_done),.eng_next_token(eng_next_token),.eng_cycles(eng_cycles),.eng_fault(eng_fault),.eng_clr_req(eng_clr_req),.eng_clr_ack(eng_clr_ack),
    .arr_rst_n(arr_rst_n),.cfg_users(cfg_users),.cfg_prompt_len(cfg_prompt_len),.cfg_gen_len(cfg_gen_len),.pr_re(1'b0),.pr_user(8'd0),.pr_pos(18'd0),.tok_valid(1'b0),.tok_user(8'd0),.tok_pos(18'd0),.tok_id(18'd0),.users_done(8'd0),.arr_fault(1'b0),
    .cq_commit_v(cq_commit_v),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),.cq_kind(cq_kind),.cq_status(cq_status),
    .step_issue_v(step_issue_v),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),.step_retire_v(step_retire_v),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),.host_idle(host_idle),.host_observer_fault(host_observer_fault));

wire rx_v,tx_cr;wire[511:0]rx_d;wire rx_cr,tx_v,bridge_fault,bridge_bad,bridge_owned;wire[511:0]tx_d;
reg allow_aw=1,allow_w=1;
 wire bridge_awready,bridge_wready;
 assign m_awready=bridge_awready&&allow_aw;
 assign m_wready=bridge_wready&&allow_w;
 qkd_host_axi_packet_rc #(.ENABLE_RETAINED_COMMIT(1)) bridge(.ck(clk),.rst_n(rst_n),.raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),.health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.retained_bad_i(rc_bad),.retained_bad_o(bridge_bad),.retained_owned_o(bridge_owned),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.fault(bridge_fault),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),.s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(s_wstrb),.s_bvalid(s_bvalid),.s_bready(s_bready),.s_bresp(s_bresp),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),.s_rvalid(s_rvalid),.s_rready(s_rready),.s_rdata(s_rdata),.s_rresp(s_rresp),.m_arvalid(m_arvalid),.m_arready(m_arready),.m_araddr(m_araddr),.m_rvalid(m_rvalid),.m_rready(m_rready),.m_rdata(m_rdata),.m_rresp(m_rresp),.m_rlast(m_rlast),.m_awvalid(m_awvalid&&allow_aw),.m_awready(bridge_awready),.m_awaddr(m_awaddr),.m_wvalid(m_wvalid&&allow_w),.m_wready(bridge_wready),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_bvalid(m_bvalid),.m_bready(m_bready),.m_bresp(m_bresp));

 // Actual SRAM prompt boundary, complete OLD read and capture/lane/valid path.
 wire prompt_fault;
 qkd_host_prompt_capture_pins prompt(.ck(clk),.rst_n(rst_n),.we(pb_we),.re(pb_re),.waddr(pb_waddr[12:0]),.raddr(pb_raddr[12:0]),.wdata(pb_wdata),.q(pb_q),.fault(prompt_fault));
 wire[181:0]hc;wire[743:0]tk;wire[119:0]ctl_res;
 wire package_start_v;wire[17:0]package_token,package_pos;wire[1:0]package_gen;
 reg fixture_package_ready=1,fixture_abort=0;
 reg[7:0]fixture_service_ready=8'hff;
 wire[7:0]service_ready8;wire[127:0]service_epoch8;
 qkd_host_ctl_service_pins_rc #(.ENABLE_SERVICE(1),.WDOG(FIXTURE_WDOG)) ctl(.ck(clk),.rst_n(rst_n),.sys_ready(fixture_package_ready),.pb_fault(prompt_fault),.die_id(3'd0),.req({kv_base,eng_pos,eng_token,eng_start}),.pr(143'd0),.tk(tk),.service_abort(fixture_abort),.service_ready(1'b1),.begin_block(1'b0),.epoch_fault(1'b0),.service_ready8(service_ready8),.hc(hc),.res(ctl_res),.package_start_v(package_start_v),.package_token(package_token),.package_pos(package_pos),.package_gen(package_gen));
 assign eng_done=ctl_res[0];assign eng_fault=ctl_res[1];assign eng_next_token=ctl_res[19:2];assign eng_cycles=ctl_res[83:52];
 wire cmd_v,cmd_cr,hc_accept_v;wire[181:0]cmd_hc;wire[17:0]hc_token,hc_pos;wire[1:0]hc_gen;
 wire hc_station_fault;
 qkd_host_hc_station_rc station(.ck(clk),.rst_n(rst_n),.die_id(3'd0),.raw_hc(hc),.cmd_cr(cmd_cr),.cmd_v(cmd_v),.cmd_hc(cmd_hc),.source_cr(),.available(),.fault(hc_station_fault),.hc_accept_v(hc_accept_v),.hc_token(hc_token),.hc_pos(hc_pos),.hc_gen(hc_gen));
 wire[7:0]ctrl_rx_v,ctrl_rx_cr,ctrl_tx_v,ctrl_tx_cr,ctrl_fault;
 wire[4095:0]ctrl_rx_d,ctrl_tx_d;
 wire[181:0]local_hc[8];wire[92:0]local_tk[8];
 wire[7:0]epoch_v;wire[15:0]shared_epoch[8];
 wire[7:0]token_request_v,token_grant_ready,ctrl_cancel_v,ctrl_cancel_done,ctrl_cancel_fault;
 wire[17:0]token_request_token[8],token_request_pos[8];wire[1:0]token_request_gen[8];
 wire[58:0]ctrl_cancel_tag[8];wire[1:0]ctrl_cancel_gen[8];wire[3:0]ctrl_cancel_drained[8];
 wire[7:0]allocated_rank_v,allocated_rank_delivered;wire[15:0]allocated_rank_epoch[8];wire[17:0]allocated_rank_token[8],allocated_rank_pos[8];wire[1:0]allocated_rank_gen[8];
 wire coordinator_request_ready,grant_valid,allocated_valid,allocated_delivered;
 wire[15:0]grant_epoch;wire[17:0]grant_token,grant_pos;wire[1:0]grant_gen;wire[58:0]grant_tag;
 wire request_allow,issue_ready,binding_valid,join_fault;wire[1:0]pending_phase;
 wire[15:0]bound_client,pending_client;wire[7:0]bound_slot,pending_slot;wire[17:0]pending_pos;
 wire[1:0]bound_descgen,bound_gen;wire[58:0]bound_request_tag,bound_terminal_tag;
 wire[7:0]peer_rx_valid,peer_rx_ready,peer_tx_valid,peer_tx_ready;wire[4095:0]peer_rx_data,peer_tx_data;
 wire[7:0]rank_tx_valid,rank_tx_ready;wire[4095:0]rank_tx_data;reg hold_rank7_result_return=0;
 wire alloc_fire,terminal_accepted,post_retired;wire[58:0]terminal_accept_tag;wire[1:0]terminal_accept_gen;wire[58:0]alloc_tag,acknowledged_tag,post_tag;wire[1:0]alloc_gen,acknowledged_gen,post_gen;
 wire dispatch_valid,dispatched,coordinator_fault,post_pending;
 wire[7:0]accepted_ranks;wire[58:0]cohort_tag;wire[1:0]cohort_gen;
 reg engine_result_v=0;reg[58:0]engine_result_tag=0;reg[1:0]engine_result_gen=0;
 reg engine_result_fault=0;reg[17:0]engine_result_token=0;wire engine_result_cr;
 wire[7:0]ep_request_v,ep_request_cr,ep_result_cr,ep_result_v,ep_result_done,ep_result_fault,ep_owned,ep_protocol_fault,ep_cancel_released;
 wire[58:0]ep_request_tag[8],ep_result_tag[8],release_tag[8];wire[31:0]ep_trace[8],ep_result_value[8],ep_result_cycles[8];
 wire[1:0]ep_request_gen[8],ep_result_gen[8],release_gen[8];wire[17:0]ep_request_token[8],ep_request_pos[8],ep_result_token[8];wire[3:0]ep_result_cause[8];
 wire[7:0]cancel_release_v,rank_fault,ep_bad,reset_request,retrain_request,recovery_clear;
 reg[7:0]fixture_drains=8'hff;reg[7:0]fixture_native_ready=8'hff;
 reg fixture_certificate_v=0; // Explicit conditional service certificate fixture, not primitive health coverage.
 integer ctrl_emitted,ctrl_consumed;
 native_join_ctrl_link ctrl_link(.clk(clk),.por_n(raw_por_n),.tx_v(ctrl_tx_v),.tx_d(ctrl_tx_d),.tx_cr(ctrl_tx_cr),.rx_v(ctrl_rx_v),.rx_d(ctrl_rx_d),.rx_cr(ctrl_rx_cr),.emitted(ctrl_emitted),.consumed(ctrl_consumed));
 for(genvar d=0;d<8;d++)begin:ranks
  wire[743:0]ctk;wire[7:0]cready;wire[127:0]cepoch;
  wire cr_unused;
  wire hold_return=d==7&&hold_rank7_result_return&&rank_tx_data[512*d+:8]==8'd4;
  assign peer_rx_valid[d]=rank_tx_valid[d]&&!hold_return;
  assign rank_tx_ready[d]=peer_rx_ready[d]&&!hold_return;
  assign peer_rx_data[512*d+:512]=rank_tx_data[512*d+:512];
  qkd_host_ctrl_token_service_packet_collected #(.DIE(d),.ENABLE_SERVICE(1),.ENABLE_TOKEN(1)) ctrl(
   .ck(clk),.rst_n(rst_n),.die_id(3'(d)),.rx_v(ctrl_rx_v[d]),.rx_d(ctrl_rx_d[512*d+:512]),.rx_cr(ctrl_rx_cr[d]),.tx_v(ctrl_tx_v[d]),.tx_d(ctrl_tx_d[512*d+:512]),.tx_cr(ctrl_tx_cr[d]),
   .local_tk(local_tk[d]),.local_kst(10'd0),.local_boot(2'b11),.cmd_v(d==0?cmd_v:1'b0),.cmd_hc(cmd_hc),.cmd_cr(cr_unused),.hc(local_hc[d]),.tk8(ctk),.kst8(),.boot8(),.seen(),.fault(ctrl_fault[d]),
   .startup_allowed(1'b1),.local_service_ready(fixture_service_ready[d]),.local_service_epoch(16'd0),.begin_v(1'b0),.begin_epoch(16'd0),.begin_cr(),.begin_available(),.service_begin_v(),.service_begin_epoch(),.pending_advertised(),.pending_epoch(),.service_ready8(cready),.pending_ack8(),.service_epoch8(cepoch),.ingest_permission(),
   .por_n(raw_por_n),.token_wrap_fence_valid(1'b0),.token_wrap_drained(1'b0),.token_wrap_link_reset_seen(1'b0),.token_wrap_retraining_done(1'b0),.token_allocator_fault(coordinator_fault),.package_abort(eng_fault),.abort_drained({4{fixture_drains[d]}}),
   .token_request_valid(token_request_v[d]),.token_request_ready(d==0?(coordinator_request_ready&&request_allow):1'b0),.token_request_token(token_request_token[d]),.token_request_position(token_request_pos[d]),.token_request_generation(token_request_gen[d]),
   .token_grant_valid(d==0?grant_valid:1'b0),.token_grant_ready(token_grant_ready[d]),.token_grant_epoch(grant_epoch),.token_grant_token(grant_token),.token_grant_position(grant_pos),.token_grant_generation(grant_gen),.token_grant_tag(grant_tag),
   .allocated_valid(d==0?allocated_valid:allocated_rank_v[d]),.allocated_delivered(d==0?allocated_delivered:allocated_rank_delivered[d]),.allocated_epoch(d==0?grant_epoch:allocated_rank_epoch[d]),.allocated_token(d==0?grant_token:allocated_rank_token[d]),.allocated_position(d==0?grant_pos:allocated_rank_pos[d]),.allocated_generation(d==0?grant_gen:allocated_rank_gen[d]),
   .token_epoch_valid(epoch_v[d]),.token_epoch(shared_epoch[d]),.cancel_valid(ctrl_cancel_v[d]),.cancel_tag(ctrl_cancel_tag[d]),.cancel_generation(ctrl_cancel_gen[d]),.cancel_done(ctrl_cancel_done[d]),.cancel_fault(ctrl_cancel_fault[d]),.cancel_drained(ctrl_cancel_drained[d]),.terminal_accepted(terminal_accepted));
  if(d==0)begin assign tk=ctk;assign cmd_cr=cr_unused;assign service_ready8=cready;assign service_epoch8=cepoch;end
  qkd_host_native_token_endpoint_cancel_rc #(.ENABLE_NATIVE(1),.ENABLE_RETAINED_COMMIT(1)) endpoint(
   .raw_por_n(raw_por_n),.warm_rst_n(warm_rst_n),.pll_locked_i(pll_locked_i),.health_bad_i(health_bad_i),.health_armed_i(health_armed_i),.execution_restart_i(execution_restart_i),.role_fault_i(role_fault_i),.retained_bad_o(ep_bad[d]),.retained_owned_o(),.retained_armed_o(),
   .ck(clk),.por_n(raw_por_n),.rst_n(rst_n),.hc(local_hc[d]),.legacy_tk(93'd0),.image_ready(fixture_native_ready[d]),.shared_epoch_valid(epoch_v[d]),.shared_epoch(shared_epoch[d]),
   .request_v(ep_request_v[d]),.request_tag(ep_request_tag[d]),.request_trace(ep_trace[d]),.request_gen(ep_request_gen[d]),.request_token(ep_request_token[d]),.request_pos(ep_request_pos[d]),.request_cr(ep_request_cr[d]),.native_pr(),
   .result_v(ep_result_v[d]),.result_tag(ep_result_tag[d]),.result_gen(ep_result_gen[d]),.result_done(ep_result_done[d]),.result_fault(ep_result_fault[d]),.result_cause(ep_result_cause[d]),.result_token(ep_result_token[d]),.result_value(ep_result_value[d]),.result_cycles(ep_result_cycles[d]),.result_cr(ep_result_cr[d]),
   .kv_drained(fixture_drains[d]),.vm_drained(fixture_drains[d]),.collective_drained(fixture_drains[d]),.host_drained(fixture_drains[d]),.collective_busy(1'b0),.kv_flush(1'b0),.recovery_clear(recovery_clear[d]),.cancel_release_v(cancel_release_v[d]),.cancel_release_tag(release_tag[d]),.cancel_release_gen(release_gen[d]),.context_owned(ep_owned[d]),.cancel_released(ep_cancel_released[d]),.local_tk(local_tk[d]),.protocol_fault(ep_protocol_fault[d]));
  qkd_host_peer_rank_codec_rc #(.RANK(d),.ENABLE_NATIVE_OWNER_JOIN(1)) codec(
   .ck(clk),.por_n(raw_por_n),.tx_valid(rank_tx_valid[d]),.tx_data(rank_tx_data[512*d+:512]),.tx_ready(rank_tx_ready[d]),.rx_valid(peer_tx_valid[d]),.rx_data(peer_tx_data[512*d+:512]),.rx_ready(peer_tx_ready[d]),
   .request_v(ep_request_v[d]),.request_tag(ep_request_tag[d]),.request_gen(ep_request_gen[d]),.request_trace(ep_trace[d]),.request_token(ep_request_token[d]),.request_pos(ep_request_pos[d]),.request_cr(ep_request_cr[d]),.request_aborted(),
   .cancel_valid(ctrl_cancel_v[d]),.cancel_tag(ctrl_cancel_tag[d]),.cancel_gen(ctrl_cancel_gen[d]),.cancel_done(ctrl_cancel_done[d]),.cancel_fault(ctrl_cancel_fault[d]),.cancel_drained(ctrl_cancel_drained[d]),.cancel_accepted(),.cancel_release_v(cancel_release_v[d]),.cancel_release_tag(release_tag[d]),.cancel_release_gen(release_gen[d]),.cancel_released(ep_cancel_released[d]),
   .result_v(ep_result_v[d]),.result_tag(ep_result_tag[d]),.result_gen(ep_result_gen[d]),.result_done(ep_result_done[d]),.result_fault(ep_result_fault[d]),.result_cause(ep_result_cause[d]),.result_token(ep_result_token[d]),.result_value(ep_result_value[d]),.result_cycles(ep_result_cycles[d]),.result_cr(ep_result_cr[d]),
   .service_ready(fixture_service_ready[d]),.native_ready(fixture_native_ready[d]),.service_epoch(16'd0),.drained({4{fixture_drains[d]}}),.context_owned(ep_owned[d]),.links_drained(1'b1),.link_reset_seen(reset_request[d]),.retrained(retrain_request[d]),.program_ready(1'b1),.program_epoch(16'd0),.program_digest(64'h0123456789abcdef),
   .step_retire_native_valid(d==0?step_retire_native_valid:1'b0),.cq_native_valid_observed(d==0?cq_native_valid_observed:1'b0),.step_issue_v(d==0?step_issue_v:1'b0),.step_client_tag(step_client_tag),.step_slot(step_slot),.step_pos(step_pos),
   .step_retire_v(d==0?step_retire_v:1'b0),.step_retire_cq(step_retire_cq),.step_retire_client_tag(step_retire_client_tag),.step_retire_slot(step_retire_slot),.step_retire_pos(step_retire_pos),.step_retire_token(step_retire_token),
   .cq_commit_v(d==0?cq_commit_v:1'b0),.cq_client_tag(cq_client_tag),.cq_slot(cq_slot),.cq_pos(cq_pos),.cq_token(cq_token),
   .certificate_v(fixture_certificate_v),.certificate(66'd0),.certificate_prefix(32'd0),.allocated_valid(allocated_rank_v[d]),.allocated_delivered(allocated_rank_delivered[d]),.allocated_epoch(allocated_rank_epoch[d]),.allocated_token(allocated_rank_token[d]),.allocated_position(allocated_rank_pos[d]),.allocated_gen(allocated_rank_gen[d]),.reset_request(reset_request[d]),.retrain_request(retrain_request[d]),.recovery_clear(recovery_clear[d]),.fault(rank_fault[d]));
 end
 qkd_host_tp8_coordinator_rc #(.ENABLE_NATIVE_OWNER_JOIN(1)) coordinator(
  .alloc_fire(alloc_fire),.alloc_tag(alloc_tag),.alloc_gen(alloc_gen),.join_client(pending_client),.join_slot(pending_slot),.join_pos(pending_pos),
  .terminal_accept_tag(terminal_accept_tag),.terminal_accept_gen(terminal_accept_gen),.terminal_accepted(terminal_accepted),.acknowledged_tag(acknowledged_tag),.acknowledged_gen(acknowledged_gen),.post_retired(post_retired),.post_tag(post_tag),.post_gen(post_gen),
  .ck_codec(clk),.ck_lifecycle(clk),.ck_post(clk),.por_n(raw_por_n),.peer_rx_valid(peer_rx_valid),.peer_rx_data(peer_rx_data),.peer_rx_ready(peer_rx_ready),.peer_tx_valid(peer_tx_valid),.peer_tx_data(peer_tx_data),.peer_tx_ready(peer_tx_ready),
  .token_request_valid(token_request_v[0]&&request_allow),.token_request_token(token_request_token[0]),.token_request_position(token_request_pos[0]),.token_request_gen(token_request_gen[0]),.token_request_ready(coordinator_request_ready),
  .token_grant_valid(grant_valid),.token_grant_ready(token_grant_ready[0]),.token_grant_epoch(grant_epoch),.token_grant_token(grant_token),.token_grant_position(grant_pos),.token_grant_gen(grant_gen),.token_grant_tag(grant_tag),.allocated_valid(allocated_valid),.allocated_delivered(allocated_delivered),
  .engine_admit_ready(1'b1),.dispatch_valid(dispatch_valid),.dispatched(dispatched),.cohort_tag(cohort_tag),.cohort_gen(cohort_gen),.accepted_ranks(accepted_ranks),.participant_trace(),.participant_token(),.participant_pos(),
  .engine_result_v(engine_result_v),.engine_result_tag(engine_result_tag),.engine_result_gen(engine_result_gen),.engine_result_done(1'b1),.engine_result_fault(engine_result_fault),.engine_result_cause(engine_result_fault?4'd2:4'd0),.engine_result_token(engine_result_token),.engine_result_value(32'h3f800000),.engine_result_cycles(32'd24),.engine_result_cr(engine_result_cr),
  .program_consensus(),.program_epoch(),.program_digest(),.certificate_valid(),.certificate(),.certificate_prefix(),.wrap_locked(),.identity_fault(),.recovery_complete(),.post_pending(post_pending),.fault(coordinator_fault));
 wire[17:0]bound_pos;wire[1:0]pending_descgen;wire[17:0]pending_input;
 wire binding_certified;
 wire[86:0]certificate_key_actual={native_certificate_client,native_certificate_slot,native_certificate_descgen,native_certificate_tag,native_certificate_gen};
 reg[86:0]certificate_key_to_join;
 always @*begin
  certificate_key_to_join=certificate_key_actual;
  if(case_id==10)certificate_key_to_join[45]=!certificate_key_actual[45];
  if(case_id==11)certificate_key_to_join[0]=!certificate_key_actual[0];
  if(case_id==12)certificate_key_to_join[44:39]=0;
  if(case_id==13)certificate_key_to_join[38:21]=gold_next(health_step);
 end
 qkd_host_native_owner_join_rc #(.ENABLE_NATIVE_OWNER_JOIN(1)) join_owner(
  .clk(clk),.raw_por_n(raw_por_n),.issue_fire(issue_fire_v),.issue_client(issue_client),.issue_slot(issue_slot),.issue_desc_gen(issue_descgen),.issue_position(issue_pos),.issue_input_token(issue_token),
  .package_accept_v(package_start_v),.package_position(package_pos),.package_input_token(package_token),.package_gen(package_gen),.hc_accept_v(hc_accept_v),.hc_position(hc_pos),.hc_input_token(hc_token),.hc_gen(hc_gen),
  .request_v(token_request_v[0]),.request_position(token_request_pos[0]),.request_input_token(token_request_token[0]),.request_gen(token_request_gen[0]),.allocation_fire(alloc_fire),.allocation_tag(alloc_tag),.allocation_gen(alloc_gen),
  .terminal_v(terminal_accepted),.terminal_tag(terminal_accept_tag),.terminal_gen(terminal_accept_gen),
  .raw_done_v(raw_done_v),.raw_client(raw_done_client),.raw_slot(raw_done_slot),.raw_desc_gen(raw_done_descgen),.raw_position(raw_done_pos),.raw_unready(raw_done_unready),.raw_report_needed(raw_done_report_needed),
  .certificate_v(native_certificate_v),.certificate_health_bound(health_native_valid),.certificate_key(certificate_key_to_join),
  .event_copy_v(event_insert_v&&event_native_valid),.event_key({event_client,event_slot,event_descgen,event_native_tag,event_native_gen}),
  .prompt_retired_v(report_drained_v&&!report_drained_cq&&report_drained_native_valid),.prompt_key({report_drained_client,report_drained_slot,report_drained_descgen,report_drained_tag,report_drained_gen}),
  .cq_offer_native_valid(native_cq_prospective_native_valid),.cq_offer_key(native_cq_prospective_key),.cq_offer_ok(native_cq_offer_ok),
  .cq_b_v(report_drained_v&&report_drained_cq&&report_drained_native_valid),.cq_key({report_drained_client,report_drained_slot,report_drained_descgen,report_drained_tag,report_drained_gen}),
  .post_retired_v(post_retired),.post_tag(post_tag),.post_gen(post_gen),.issue_ready(issue_ready),.request_allow(request_allow),.binding_valid(binding_valid),.protocol_fault(join_fault),.pending_phase(pending_phase),
  .pending_client(pending_client),.pending_slot(pending_slot),.pending_desc_gen(pending_descgen),.pending_position(pending_pos),.pending_input_token(pending_input),
  .bound_client(bound_client),.bound_slot(bound_slot),.bound_position(bound_pos),.bound_desc_gen(bound_descgen),.bound_native_gen(bound_gen),.bound_request_tag(bound_request_tag),.bound_terminal_tag(bound_terminal_tag),.raw_cleanup_allow(),.binding_certified(binding_certified));
 assign native_issue_ready=issue_ready;
 assign native_bound_valid=binding_valid;assign native_bound_tag=bound_request_tag;assign native_bound_gen=bound_gen;assign native_bound_descgen=bound_descgen;
 assign native_bound_client=bound_client;assign native_bound_slot=bound_slot;assign native_bound_pos=bound_pos;assign native_join_fault=join_fault;
 // Health collector is a typed COMPONENT environment. Its key is predicted
 // from submitted descriptor and known engine fixture outputs, never DUT binding.
 integer health_step=0;
 function automatic[17:0]gold_input(input integer step);
  case(step)0:gold_input=70001;1:gold_input=70003;2:gold_input=80001;3:gold_input=90001;default:gold_input=0;endcase
 endfunction
 function automatic[17:0]gold_next(input integer step);
  case(step)0:gold_next=70002;1:gold_next=80001;2:gold_next=90001;3:gold_next=100001;default:gold_next=0;endcase
 endfunction
 assign health_native_valid=health_armed_i;
 assign health_native_tag={16'(health_step),6'd37,gold_input(health_step),13'(health_step),6'd0};
 assign health_native_gen=2'(health_step+1);
 reg hold_dma_b=0;
 integer csr_acks,read_beats,write_beats,cq_entries,cq_successes,cq_errors;wire[63:0]last_cq_w0,last_cq_w1;
 native_join_host_memory memory(.clk(clk),.por_n(raw_por_n),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_cr),.rx_v(rx_v),.rx_d(rx_d),.rx_cr(rx_cr),.hold_dma_b(hold_dma_b),.csr_acks(csr_acks),.read_beats(read_beats),.write_beats(write_beats),.cq_entries(cq_entries),.cq_successes(cq_successes),.cq_errors(cq_errors),.last_cq_w0(last_cq_w0),.last_cq_w1(last_cq_w1));
 reg expected_retire_v=0,expected_retire_native=0,expected_cq_v=0,expected_cq_native=0,expected_missing_binding_fault=0;
 bit retire_markers[$],cq_markers[$];bit marker;
 always @(posedge clk)begin
  if(raw_por_n)begin
   if(step_retire_v!==expected_retire_v)$fatal(1,"RETIRE_OBSERVER_EDGE_CHANGED");
   if(step_retire_v)begin
    if(step_retire_native_valid!==expected_retire_native)$fatal(1,"RETIRE_MARKER_ALIGNMENT");
    retire_markers.push_back(step_retire_native_valid);
   end
   if(cq_commit_v!==expected_cq_v)$fatal(1,"CQ_OBSERVER_EDGE_CHANGED");
   if(cq_commit_v)begin
    if(cq_native_valid_observed!==expected_cq_native)$fatal(1,"CQ_MARKER_ALIGNMENT");
    cq_markers.push_back(cq_native_valid_observed);
   end
   if(peer_rx_valid[0]&&peer_rx_ready[0])begin
    if(peer_rx_data[7:0]==8'd6)begin
     if(retire_markers.size()==0)$fatal(1,"RETIRE_PACKET_WITHOUT_SOURCE");
     marker=retire_markers.pop_front();if(peer_rx_data[91]!==marker)$fatal(1,"RETIRE_PACKET_MARKER");
    end
    if(peer_rx_data[7:0]==8'd7)begin
     if(cq_markers.size()==0)$fatal(1,"CQ_PACKET_WITHOUT_SOURCE");
     marker=cq_markers.pop_front();if(peer_rx_data[90]!==marker)$fatal(1,"CQ_PACKET_MARKER");
    end
   end
   if(expected_missing_binding_fault&&!join_fault)$fatal(1,"MISSING_NATIVE_BINDING_WAS_NOT_FAULT");
   expected_retire_v<=raw_done_v;expected_retire_native<=raw_done_native_valid;
   expected_cq_v<=cq_dma_retired_v;
   expected_cq_native<=native_cq_prospective_native_valid;
   expected_missing_binding_fault<=raw_done_v&&!raw_done_native_valid&&!raw_done_unready;
  end
 end
 reg expected_metadata_fault=0,malformed_first_prompt_cut=0;
 integer native_cq_retirements=0;
 integer edges=0,issues=0,allocations=0,dispatches=0,raw_completions=0,post_completions=0,certificates=0,event_copies=0,cq_offers=0,terminal_accepts=0;
 integer request_counts[8],request_returns[8],result_returns[8],transport_returns[8],releases[8],raw_cleanup_due[8];
 integer engine_credits=0;reg old_rc_bad=0,native_binding_seen=0;reg rank7_return_stalled=0;reg[511:0]held_rank7_return;
 integer response_due=-1,response_step=-1,first_issue_edge=0,max_response=0;
 integer case_id=0;
 // Selected one-beat pin-channel protocol: first acceptance owns request;
 // WAIT_DROP may retain VALID through the registered ACK. Not generic AXI.
 reg aw_seen=0,aw_accepted=0,w_seen=0,w_accepted=0,ar_seen=0,ar_accepted=0;
 reg[63:0]held_awaddr,held_wdata,held_araddr;
 integer aw_accepts=0,w_accepts=0,ar_accepts=0,bridge_aw_captures=0,bridge_w_captures=0;
 reg old_mon_aw_valid=0,old_mon_w_valid=0,old_out_aw_valid=0,old_out_w_valid=0;
 reg[86:0]saved_cq_key;reg saved_cq_key_valid=0;
 // These are invariants on true exposed protocol events, not DUT mirror oracles.
 always @(posedge clk)begin
  if(raw_por_n)begin
   edges=edges+1;
   if(rank7_return_stalled&&(!rank_tx_valid[7]||rank_tx_data[3584+:512]!==held_rank7_return))$fatal(1,"REAL_RETURN_READY_VALID_PAYLOAD_CHANGED");
   rank7_return_stalled=rank_tx_valid[7]&&!rank_tx_ready[7]&&rank_tx_data[3584+:8]==8'd4;
   held_rank7_return=rank_tx_data[3584+:512];
   if(malformed_first_prompt_cut&&(rc_mirror_pos!==18'd0||rc_mirror_tok!==18'd0||rc_mirror_ngen!==18'd0))$fatal(1,"MALFORMED_FIRST_PROMPT_CERTIFIED_MIRROR pos=%0d tok=%0d ngen=%0d",rc_mirror_pos,rc_mirror_tok,rc_mirror_ngen);
   malformed_first_prompt_cut<=native_certificate_v&&case_id>=10&&case_id<=13&&health_step==0;
   if(native_certificate_v&&case_id>=10&&case_id<=13&&health_step==0)begin
    if(rc_mirror_pos!==0||rc_mirror_tok!==0||rc_mirror_ngen!==0)$fatal(1,"MALFORMED_PROMPT_INITIAL_COMMITTED_STATE_NOT_ZERO");
    $display("MALFORMED_FIRST_PROMPT_CERTIFICATE time=%0t key=%h actual=%h mirror=%0d/%0d/%0d",$time,certificate_key_to_join,certificate_key_actual,rc_mirror_pos,rc_mirror_tok,rc_mirror_ngen);
   end
   if(expected_metadata_fault&&!join_fault)$fatal(1,"CORRUPT_CERTIFICATE_WAS_ACCEPTED case=%0d",case_id);
   expected_metadata_fault<=native_certificate_v&&case_id>=10&&case_id<=13;
   if(binding_valid&&case_id<=3&&bound_request_tag!=={16'(allocations-1),6'd0,gold_input(allocations-1),13'(allocations-1),6'd0})$fatal(1,"BOUND_KEY_IS_NATIVE_TAG59");
   if(issue_fire_v)begin
    if(issue_token!=gold_input(issues)||issue_pos!=18'(issues)||issue_client!=16'h91e3||issue_slot!=0)$fatal(1,"ACTUAL_ISSUE_GOLD n=%0d tok=%0d pos=%0d",issues,issue_token,issue_pos);
    first_issue_edge=edges;
    issues=issues+1;
    $display("ISSUE e=%0d input=%0d pos=%0d owner=%h/%0d",edges,issue_token,issue_pos,issue_client,issue_descgen);
   end
   if(alloc_fire)begin
    if(alloc_tag!=={16'(allocations),6'd0,gold_input(allocations),13'(allocations),6'd0}||alloc_gen!=2'(allocations+1))$fatal(1,"ACTUAL_ALLOCATION_GOLD n=%0d tag=%h gen=%0d",allocations,alloc_tag,alloc_gen);
    if(allocations>post_completions)$fatal(1,"ALLOCATION_BEFORE_PRIOR_POST");
    health_step<=allocations;allocations=allocations+1;
    $display("ALLOC e=%0d tag=%h gen=%0d",edges,alloc_tag,alloc_gen);
   end
   for(integer r=0;r<8;r=r+1)begin
    if(peer_rx_valid[r]&&peer_rx_ready[r]&&peer_rx_data[512*r+:8]==8'd4)transport_returns[r]=transport_returns[r]+1;
    if(case_id==4&&ep_result_v[r]&&ep_result_done[r]&&fixture_drains[r])raw_cleanup_due[r]=edges+6;
    if(case_id==4&&raw_cleanup_due[r]>=0&&edges>=raw_cleanup_due[r])begin
     if(ep_owned[r])$fatal(1,"RAW_CLEANUP_HEALTH_VETO rank=%0d",r);
     raw_cleanup_due[r]=-1;
    end
    if(ep_request_v[r])begin
     if(ep_request_tag[r]!=={16'(request_counts[r]),6'd0,gold_input(request_counts[r]),13'(request_counts[r]),6'd0}||ep_request_gen[r]!=2'(request_counts[r]+1))$fatal(1,"RANK_REQUEST_ID rank=%0d n=%0d",r,request_counts[r]);
     request_counts[r]=request_counts[r]+1;
    end
    if(ep_request_cr[r])request_returns[r]=request_returns[r]+1;
    if(ep_result_cr[r])result_returns[r]=result_returns[r]+1;
    if(ep_cancel_released[r])begin
     if(terminal_accepts==0)$fatal(1,"RELEASE_BEFORE_REAL_TERMINAL rank=%0d",r);
     releases[r]=releases[r]+1;
    end
   end
   if(engine_result_cr)begin
    engine_credits=engine_credits+1;
    for(integer r=0;r<8;r=r+1)if(transport_returns[r]<dispatches)$fatal(1,"ENGINE_CREDIT_BEFORE_ALL_RESULT_RETURNS rank=%0d",r);
   end
   if(terminal_accepted)terminal_accepts=terminal_accepts+1;
   if(dispatch_valid)begin
    if(accepted_ranks!=8'hff)$fatal(1,"DISPATCH_MISSING_RANK");
    if(response_due!=-1)$fatal(1,"DUPLICATE_ENGINE_DISPATCH");
    if(cohort_tag!=={16'(dispatches),6'd0,gold_input(dispatches),13'(dispatches),6'd0})$fatal(1,"DISPATCH_GOLD");
    response_step=dispatches;dispatches=dispatches+1;response_due=edges+24;
   end
   if(binding_valid)native_binding_seen=1;
   if((case_id==6||case_id==8)&&native_binding_seen&&raw_completions==0&&!binding_valid)$fatal(1,"ALLOCATED_CANCEL_OWNER_LOST_BEFORE_RAWDONE");
   if((case_id==6||case_id==8)&&cq_errors!=0&&raw_completions==0)$fatal(1,"ACTIVE_FAILURE_REPORT_BEFORE_RAW_CLEANUP");
   if(rc_bad&&!old_rc_bad)$display("RETAINED_BAD time=%0t e=%0d raw=%0d errorCQ=%0d",$time,edges,raw_completions,cq_errors);
   old_rc_bad=rc_bad;
   if(raw_done_v)begin
    if((case_id==6||case_id==8)&&(!raw_done_native_valid||raw_done_unready))$fatal(1,"ALLOCATED_CANCEL_RELABELLED_NO_NATIVE");
    if(!raw_done_native_valid&&case_id!=5)$fatal(1,"UNEXPECTED_NO_NATIVE");
    raw_completions=raw_completions+1;
    if(edges-first_issue_edge>max_response)max_response=edges-first_issue_edge;
    first_issue_edge=edges;
    $display("RAW_DONE time=%0t e=%0d native=%b unready=%b needed=%b",$time,edges,raw_done_native_valid,raw_done_unready,raw_done_report_needed);
   end
   if(native_certificate_v)certificates=certificates+1;
   if(event_insert_v&&event_native_valid)event_copies=event_copies+1;
   if(cq_offer_v&&cq_native_valid)begin
    if(case_id<=3||case_id==14)begin
     if(!native_cq_offer_ok)$fatal(1,"UNCERTIFIED_CQ_SUCCESS_OFFER");
     if(cq_native_tag!=={16'(cq_offers+1),6'd37,gold_input(cq_offers+1),13'(cq_offers+1),6'd0})$fatal(1,"SAVED_CQ_LINEAGE n=%0d tag=%h",cq_offers,cq_native_tag);
    end
    // Native failure records own the same immutable saved-key lifetime.
    saved_cq_key={cq_offer_client,cq_offer_slot,cq_descgen,cq_native_tag,cq_native_gen};saved_cq_key_valid=1;
    cq_offers=cq_offers+1;
   end
   if(report_drained_v&&report_drained_cq&&report_drained_native_valid)begin
    if(!saved_cq_key_valid||{report_drained_client,report_drained_slot,report_drained_descgen,report_drained_tag,report_drained_gen}!==saved_cq_key)$fatal(1,"CQB_SAVED_KEY");
    saved_cq_key_valid=0;native_cq_retirements=native_cq_retirements+1;
   end
   if(cq_dma_retired_v)$display("REAL_CQB time=%0t e=%0d native=%b",$time,edges,native_cq_prospective_native_valid);
   if(post_retired)begin
    if(post_completions>=1&&case_id<=3&&native_cq_retirements<post_completions)$fatal(1,"POST_BEFORE_REAL_CQB");
    post_completions=post_completions+1;$display("POST e=%0d tag=%h",edges,post_tag);end
   if(!aw_seen&&m_awvalid)begin
    aw_seen=1;aw_accepted=m_awready;held_awaddr=m_awaddr;
    if(m_awready)begin aw_accepts=aw_accepts+1;$display("PIN_FIRST_AW_ACCEPT e=%0d addr=%h",edges,m_awaddr);end
   end else if(aw_seen&&!aw_accepted)begin
    if(!m_awvalid||m_awaddr!==held_awaddr)$fatal(1,"OFFERED_AW_CHANGED_BEFORE_ACCEPTANCE");
    if(m_awready)begin aw_accepted=1;aw_accepts=aw_accepts+1;$display("PIN_FIRST_AW_ACCEPT e=%0d addr=%h",edges,m_awaddr);end
   end else if(aw_seen&&aw_accepted&&!m_awvalid)begin aw_seen=0;aw_accepted=0;end
   if(!w_seen&&m_wvalid)begin
    w_seen=1;w_accepted=m_wready;held_wdata=m_wdata;
    if(m_wready)begin w_accepts=w_accepts+1;$display("PIN_FIRST_W_ACCEPT e=%0d data=%h",edges,m_wdata);end
   end else if(w_seen&&!w_accepted)begin
    if(!m_wvalid||m_wdata!==held_wdata)$fatal(1,"OFFERED_W_CHANGED_BEFORE_ACCEPTANCE");
    if(m_wready)begin w_accepted=1;w_accepts=w_accepts+1;$display("PIN_FIRST_W_ACCEPT e=%0d data=%h",edges,m_wdata);end
   end else if(w_seen&&w_accepted&&!m_wvalid)begin w_seen=0;w_accepted=0;end
   if(!ar_seen&&m_arvalid)begin
    ar_seen=1;ar_accepted=m_arready;held_araddr=m_araddr;
    if(m_arready)ar_accepts=ar_accepts+1;
   end else if(ar_seen&&!ar_accepted)begin
    if(!m_arvalid||m_araddr!==held_araddr)$fatal(1,"OFFERED_AR_CHANGED_BEFORE_ACCEPTANCE");
    if(m_arready)begin ar_accepted=1;ar_accepts=ar_accepts+1;end
   end else if(ar_seen&&ar_accepted&&!m_arvalid)begin ar_seen=0;ar_accepted=0;end
   // Capture ACKs are counted even on VALID-drop edges and while WAIT_DROP
   // keeps an accepted request visible. An extra real capture cannot disappear.
   if(bridge_awready)begin bridge_aw_captures=bridge_aw_captures+1;$display("BRIDGE_AW_CAPTURE_ACK e=%0d n=%0d out_valid=%b",edges,bridge_aw_captures,m_awvalid);end
   if(bridge_wready)begin bridge_w_captures=bridge_w_captures+1;$display("BRIDGE_W_CAPTURE_ACK e=%0d n=%0d out_valid=%b",edges,bridge_w_captures,m_wvalid);end
   if(bridge_aw_captures>aw_accepts)$fatal(1,"EXTRA_BRIDGE_AW_CAPTURE_ACK captures=%0d unique=%0d out_valid=%b",bridge_aw_captures,aw_accepts,m_awvalid);
   if(bridge_w_captures>w_accepts)$fatal(1,"EXTRA_BRIDGE_W_CAPTURE_ACK captures=%0d unique=%0d out_valid=%b",bridge_w_captures,w_accepts,m_wvalid);
   if(mon_aw_ack)$display("PIN_RETURNED_AW_ACK e=%0d source_valid=%b out_valid=%b",edges,mon_aw_source_valid,m_awvalid);
   if(mon_w_ack)$display("PIN_RETURNED_W_ACK e=%0d source_valid=%b out_valid=%b",edges,mon_w_source_valid,m_wvalid);
   if(old_mon_aw_valid&&!mon_aw_source_valid)$display("PIN_AW_SOURCE_VALID_DROP e=%0d",edges);
   if(old_mon_w_valid&&!mon_w_source_valid)$display("PIN_W_SOURCE_VALID_DROP e=%0d",edges);
   if(old_out_aw_valid&&!m_awvalid)$display("PIN_AW_OUTPUT_VALID_DROP e=%0d",edges);
   if(old_out_w_valid&&!m_wvalid)$display("PIN_W_OUTPUT_VALID_DROP e=%0d",edges);
   old_mon_aw_valid=mon_aw_source_valid;old_mon_w_valid=mon_w_source_valid;old_out_aw_valid=m_awvalid;old_out_w_valid=m_wvalid;
   if((case_id<=3||case_id==14)&&(join_fault||coordinator_fault||bridge_fault||hc_station_fault||(|ctrl_fault)||(|rank_fault)||(|ep_protocol_fault)||rc_bad))$fatal(1,"HEALTHY_SOURCE_FAULT e=%0d join=%b coord=%b bridge=%b hc=%b ctrl=%h rank=%h ep=%h rc=%b",edges,join_fault,coordinator_fault,bridge_fault,hc_station_fault,ctrl_fault,rank_fault,ep_protocol_fault,rc_bad);
  end
 end
 always @(negedge clk)begin
  engine_result_v=0;
  if(raw_por_n&&response_due>=0&&edges>=response_due)begin
   engine_result_v=1;engine_result_tag={16'(response_step),6'd37,gold_input(response_step),13'(response_step),6'd0};engine_result_gen=2'(response_step+1);engine_result_token=gold_next(response_step);response_due=-1;
   $display("ENGINE_RESULT e=%0d step=%0d tag=%h next=%0d",edges,response_step,engine_result_tag,engine_result_token);
  end
 end
 task automatic tick(input integer n);repeat(n)@(negedge clk);#1;endtask
 initial begin
  if(!$value$plusargs("CASE=%d",case_id))case_id=0;
  if(case_id<0||case_id==9||case_id>14)$fatal(1,"CASE_NOT_IMPLEMENTED id=%0d",case_id);
  if((case_id==6||case_id==8)&&FIXTURE_WDOG!=512)$fatal(1,"CANCELLATION_REQUIRES_SEPARATE_TYPED_WDOG512_BUILD");
  if(case_id==14)hold_rank7_result_return=1;
  if(case_id==1)allow_aw=0;
  if(case_id==2)allow_w=0;
  if(case_id==5)fixture_package_ready=0;
  for(integer r=0;r<8;r=r+1)begin request_counts[r]=0;request_returns[r]=0;result_returns[r]=0;releases[r]=0;raw_cleanup_due[r]=-1;transport_returns[r]=0;end
  memory.descriptor(0,16'h91e3,8'd1,8'd1,8'd0,16'd2,16'd3,64'h3000);
  memory.prompt_word(0,18'd70001,18'd70003);
  if(case_id==7)begin
   memory.descriptor(1,16'h91e3,8'd1,8'd1,8'd0,16'd2,16'd3,64'h3000);
   memory.descriptor(2,16'h91e3,8'd2,8'd1,8'd0,16'd2,16'd3,64'h3000);
  end
  tick(4);raw_por_n=1;warm_rst_n=1;pll_locked_i=1;rst_n=1;health_armed_i=1;health_cutoff_i=1;
  tick(12);fixture_certificate_v=1;tick(1);fixture_certificate_v=0;
  tick(100); // Fixture boot/service packets complete; not an ownership/checker mask.
  memory.csr_write('h010,'h1000);memory.csr_write('h018,4);memory.csr_write('h024,'h2000);memory.csr_write('h02c,4);memory.csr_write('h008,1);memory.csr_write('h01c,case_id==7?3:1);
  if(case_id==14)begin
   wait(transport_returns[0]==1&&transport_returns[1]==1&&transport_returns[2]==1&&transport_returns[3]==1&&transport_returns[4]==1&&transport_returns[5]==1&&transport_returns[6]==1&&rank_tx_valid[7]&&rank_tx_data[3584+:8]==8'd4);
   tick(24);
   if(transport_returns[7]!=0||engine_credits!=0)$fatal(1,"RESULT_RETURN_STALL_NOT_PRESERVED");
   $display("REAL_RESULT_RETURN_STALL e=%0d endpoint_credit7=%0d wire_return7=%0d engine_credits=%0d",edges,result_returns[7],transport_returns[7],engine_credits);
   hold_rank7_result_return=0;
  end
  if(case_id==6)begin
   wait(token_request_v[0]);@(negedge clk);fixture_service_ready=0;
   wait(allocated_valid);#1;
   if(allocated_delivered)$fatal(1,"CANCEL_PREGRANT_NOT_ESTABLISHED_ALREADY_DELIVERED");
   $display("CANCEL_ACCEPTED_UNDELIVERED e=%0d tag=%h",edges,grant_tag);
   wait(eng_fault);#1;
   if(allocated_delivered)$fatal(1,"CANCEL_PREGRANT_NOT_ESTABLISHED_DELIVERY_OCCURRED");
  end
  if(case_id==8)begin
   wait(allocated_delivered);@(negedge clk);fixture_drains[7]=0;
   wait(eng_fault);tick(64);
   if(terminal_accepted||!ep_owned[7])$fatal(1,"CANCEL_POSTGRANT_DRAIN_BYPASS");
   fixture_drains[7]=1;
  end
  if(case_id>=10&&case_id<=13)wait(join_fault);
  if(case_id==4||case_id==7)begin
   if(case_id==7)wait(cq_errors==2);
   else wait(request_counts[0]==1&&request_counts[1]==1&&request_counts[2]==1&&request_counts[3]==1&&request_counts[4]==1&&request_counts[5]==1&&request_counts[6]==1&&request_counts[7]==1);
   @(negedge clk);health_bad_i=1;tick(1);health_bad_i=0;
  end
  if(case_id==4||case_id==5||case_id==6||case_id==7||case_id==8||(case_id>=10&&case_id<=13))begin
   wait(cq_errors>=(case_id==7?3:1)&&raw_completions!=0);tick(200);
   if(cq_successes!=0||!rc_bad||!bridge_bad||raw_completions==0)$fatal(1,"FAIL_STOP_REPORT_OR_RAWCLEANUP errors=%0d success=%0d raw=%0d rc=%b bridge=%b",cq_errors,cq_successes,raw_completions,rc_bad,bridge_bad);
   if(case_id==5)begin
    if(allocations!=0||dispatches!=0||issues!=1)$fatal(1,"NO_NATIVE_FABRICATED_OWNER");
    for(integer r=0;r<8;r=r+1)if(request_counts[r]!=0)$fatal(1,"NO_NATIVE_REQUEST rank=%0d",r);
   end else if(case_id==6)begin
    if(dispatches!=0||result_returns[0]!=0)$fatal(1,"PREGRANT_CANCEL_EXECUTED_ENGINE");
    for(integer r=0;r<8;r=r+1)if(request_counts[r]!=request_returns[r]||ep_owned[r])$fatal(1,"PREGRANT_CANCEL_RAW_DRAIN rank=%0d requests=%0d returns=%0d owned=%b",r,request_counts[r],request_returns[r],ep_owned[r]);
   end else begin
    for(integer r=0;r<8;r=r+1)if(request_counts[r]!=request_returns[r]||request_counts[r]!=result_returns[r]||ep_owned[r])$fatal(1,"FAILED_NATIVE_RAW_DRAIN rank=%0d request=%0d reqcr=%0d resultcr=%0d owned=%b",r,request_counts[r],request_returns[r],result_returns[r],ep_owned[r]);
   end
   if(case_id==5&&(post_completions!=0||terminal_accepts!=0))$fatal(1,"NO_NATIVE_FABRICATED_POST");
   if((case_id==6||case_id==8)&&(raw_completions!=1||allocations!=1||issues!=1))$fatal(1,"CANCEL_LATE_RAW_CLEANUP_COUNT raw=%0d alloc=%0d issues=%0d",raw_completions,allocations,issues);
   if(cq_errors!=(case_id==7?3:1))$fatal(1,"FAILURE_REPORT_EXACT_COUNT got=%0d",cq_errors);
   $display("NATIVE_JOIN_PASS FUNCTIONAL_ONLY case=%0d errors=%0d raw=%0d allocations=%0d NO_NATIVE_conditional=%b",case_id,cq_errors,raw_completions,allocations,case_id==5);
   $finish;
  end
  if(case_id==1)begin
   wait(m_wvalid&&m_wready);tick(12);allow_aw=1;
  end
  if(case_id==2)begin
   wait(m_awvalid&&m_awready);tick(12);allow_w=1;
  end
  if(case_id==3)begin
   wait(cq_offer_v);hold_dma_b=1;
   tick(64);
   if(allocations!=post_completions+1)$fatal(1,"CQ_STALL_ACTIVE_COUNT alloc=%0d post=%0d",allocations,post_completions);
   if(!binding_valid||!post_pending)$fatal(1,"CQ_STALL_RELEASE_EARLY");
   if(pending_phase==0||issues!=allocations+1)$fatal(1,"CQ_STALL_NEXT_UNBOUND_NOT_EXERCISED pending=%0d issues=%0d alloc=%0d",pending_phase,issues,allocations);
   if(saved_cq_key_valid&&saved_cq_key[60:2]!=={16'd1,6'd37,18'd70003,13'd1,6'd0})$fatal(1,"CQ_STALL_OLD_EVENT_KEY");
   $display("CQ_STALL e=%0d pending_phase=%0d issues=%0d alloc=%0d post=%0d saved=%h",edges,pending_phase,issues,allocations,post_completions,saved_cq_key);
   hold_dma_b=0;
  end
  wait(post_completions==4);tick(24);
  if(issues!=4||allocations!=4||dispatches!=4||raw_completions!=4||certificates!=4||event_copies!=3||cq_offers!=3||cq_entries!=3)$fatal(1,"JOIN_FINAL_COUNTS issues=%0d alloc=%0d dispatch=%0d raw=%0d cert=%0d events=%0d offers=%0d CQ=%0d",issues,allocations,dispatches,raw_completions,certificates,event_copies,cq_offers,cq_entries);
  for(integer r=0;r<8;r=r+1)if(request_counts[r]!=4||request_returns[r]!=4||result_returns[r]!=4||transport_returns[r]!=4||releases[r]!=4)$fatal(1,"RANK_ACCOUNTING rank=%0d request=%0d reqcr=%0d resultcr=%0d release=%0d",r,request_counts[r],request_returns[r],result_returns[r],releases[r]);
  if(ar_accepts!=read_beats||aw_accepts!=write_beats||w_accepts!=write_beats||bridge_aw_captures!=write_beats||bridge_w_captures!=write_beats||read_beats!=5||write_beats!=6)$fatal(1,"DMA_CAPTURE_PACKET_COUNTS AR=%0d Rpackets=%0d AW=%0d W=%0d Wpackets=%0d",ar_accepts,read_beats,aw_accepts,w_accepts,write_beats);
  if(binding_valid||post_pending||(|ep_owned)||join_fault||coordinator_fault||rc_bad)$fatal(1,"FINAL_OWNERSHIP_NOT_DRAINED");
  $display("NATIVE_JOIN_PASS FUNCTIONAL_ONLY case=%0d edges=%0d H=%0d deadline=%0d extra_age_bits=3 max_response=%0d",case_id,edges,H,RESPONSE_DEADLINE,max_response);
  $finish;
 end
 // Finite scenario progress bound, not a process/build runtime deadline.
 initial begin repeat(12000)@(posedge clk);$fatal(1,"SCENARIO_NO_PROGRESS issues=%0d alloc=%0d post=%0d",issues,allocations,post_completions);end
endmodule
