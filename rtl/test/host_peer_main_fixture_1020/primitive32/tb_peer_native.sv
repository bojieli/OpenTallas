`timescale 1ns/1ps
module tb_peer_native;
reg ck_core=0;always #5 ck_core=~ck_core;
reg [15:0] program_epoch=0;
reg [63:0] program_digest=0;
reg package_abort=0;
reg [3:0] abort_drained=0;
wire o0_token_epoch_valid;
wire o1_token_epoch_valid;
reg p_token_epoch_valid=0;integer t_token_epoch_valid=0;
wire [15:0] o0_token_epoch;
wire [15:0] o1_token_epoch;
reg [15:0] p_token_epoch=0;integer t_token_epoch=0;
reg native_kv_drained=0;
reg native_vm_drained=0;
reg native_collective_drained=0;
reg native_host_drained=0;
reg service_ready=0;
wire o0_ingest_permission;
wire o1_ingest_permission;
reg p_ingest_permission=0;integer t_ingest_permission=0;
reg [15:0] local_service_epoch=0;
reg [2:0] die_id=0;
reg por_n=0;
reg pll_locked=0;
reg [9:0] local_kst=0;
reg program_ready=0;
wire [38:0] o0_hc;
wire [38:0] o1_hc;
reg [38:0] p_hc=0;integer t_hc=0;
wire [7:0] o0_seen;
wire [7:0] o1_seen;
reg [7:0] p_seen=0;integer t_seen=0;
reg host_rst_n=0;
reg [127:0] slice_boot_done=0;
reg [127:0] slice_boot_ok=0;
wire o0_service_faults;
wire o1_service_faults;
reg p_service_faults=0;integer t_service_faults=0;
reg native_admit_ready=0;
reg native_links_drained=0;
reg native_link_reset_seen=0;
reg native_retrained=0;
wire o0_peer_protocol_fault;
wire o1_peer_protocol_fault;
reg p_peer_protocol_fault=0;integer t_peer_protocol_fault=0;
wire o0_dispatch_valid;
wire o1_dispatch_valid;
reg p_dispatch_valid=0;integer t_dispatch_valid=0;
wire o0_dispatched;
wire o1_dispatched;
reg p_dispatched=0;integer t_dispatched=0;
wire [58:0] o0_cohort_tag;
wire [58:0] o1_cohort_tag;
reg [58:0] p_cohort_tag=0;integer t_cohort_tag=0;
wire [1:0] o0_cohort_gen;
wire [1:0] o1_cohort_gen;
reg [1:0] p_cohort_gen=0;integer t_cohort_gen=0;
wire [7:0] o0_accepted_ranks;
wire [7:0] o1_accepted_ranks;
reg [7:0] p_accepted_ranks=0;integer t_accepted_ranks=0;
wire [255:0] o0_participant_trace;
wire [255:0] o1_participant_trace;
reg [255:0] p_participant_trace=0;integer t_participant_trace=0;
wire [143:0] o0_participant_token;
wire [143:0] o1_participant_token;
reg [143:0] p_participant_token=0;integer t_participant_token=0;
wire [143:0] o0_participant_pos;
wire [143:0] o1_participant_pos;
reg [143:0] p_participant_pos=0;integer t_participant_pos=0;
reg engine_result_v=0;
reg [58:0] engine_result_tag=0;
reg [1:0] engine_result_gen=0;
reg engine_result_done=0;
reg engine_result_fault=0;
reg [3:0] engine_result_cause=0;
reg [17:0] engine_result_token=0;
reg [31:0] engine_result_value=0;
reg [31:0] engine_result_cycles=0;
wire o0_engine_result_cr;
wire o1_engine_result_cr;
reg p_engine_result_cr=0;integer t_engine_result_cr=0;
wire o0_program_consensus;
wire o1_program_consensus;
reg p_program_consensus=0;integer t_program_consensus=0;
wire o0_coordinator_fault;
wire o1_coordinator_fault;
reg p_coordinator_fault=0;integer t_coordinator_fault=0;
wire o0_recovery_complete;
wire o1_recovery_complete;
reg p_recovery_complete=0;integer t_recovery_complete=0;
wire o0_host_link_reset_req;
wire o1_host_link_reset_req;
reg p_host_link_reset_req=0;integer t_host_link_reset_req=0;
wire o0_host_recovery_clear;
wire o1_host_recovery_clear;
reg p_host_recovery_clear=0;integer t_host_recovery_clear=0;
wire o0_root_mux_fault;
wire o1_root_mux_fault;
reg p_root_mux_fault=0;integer t_root_mux_fault=0;
wire o0_allocated_valid;
wire o1_allocated_valid;
reg p_allocated_valid=0;integer t_allocated_valid=0;
reg native_context_owned=0;
wire o0_u_rank__u_control__por_n;
wire o1_u_rank__u_control__por_n;
reg p_u_rank__u_control__por_n=0;integer t_u_rank__u_control__por_n=0;
reg u_rank__u_control__service_ready=0;
wire o0_u_rank__peer_link_fault;
wire o1_u_rank__peer_link_fault;
reg p_u_rank__peer_link_fault=0;integer t_u_rank__peer_link_fault=0;
wire [1:0] o0_cancel_release_gen;
wire [1:0] o1_cancel_release_gen;
reg [1:0] p_cancel_release_gen=0;integer t_cancel_release_gen=0;
wire [58:0] o0_cancel_release_tag;
wire [58:0] o1_cancel_release_tag;
reg [58:0] p_cancel_release_tag=0;integer t_cancel_release_tag=0;
wire o0_cancel_release_v;
wire o1_cancel_release_v;
reg p_cancel_release_v=0;integer t_cancel_release_v=0;
reg cancel_released=0;
reg [65:0] certificate=0;
reg [31:0] certificate_prefix=0;
reg certificate_v=0;
reg [15:0] cq_client_tag=0;
reg cq_commit_v=0;
reg [17:0] cq_pos=0;
reg [7:0] cq_slot=0;
reg [17:0] cq_token=0;
wire o0_native_request_cr;
wire o1_native_request_cr;
reg p_native_request_cr=0;integer t_native_request_cr=0;
reg [1:0] native_request_gen=0;
reg [17:0] native_request_pos=0;
reg [58:0] native_request_tag=0;
reg [17:0] native_request_token=0;
reg [31:0] native_request_trace=0;
reg native_request_v=0;
wire [3:0] o0_native_result_cause;
wire [3:0] o1_native_result_cause;
reg [3:0] p_native_result_cause=0;integer t_native_result_cause=0;
reg native_result_cr=0;
wire [31:0] o0_native_result_cycles;
wire [31:0] o1_native_result_cycles;
reg [31:0] p_native_result_cycles=0;integer t_native_result_cycles=0;
wire o0_native_result_done;
wire o1_native_result_done;
reg p_native_result_done=0;integer t_native_result_done=0;
wire o0_native_result_fault;
wire o1_native_result_fault;
reg p_native_result_fault=0;integer t_native_result_fault=0;
wire [1:0] o0_native_result_gen;
wire [1:0] o1_native_result_gen;
reg [1:0] p_native_result_gen=0;integer t_native_result_gen=0;
wire [58:0] o0_native_result_tag;
wire [58:0] o1_native_result_tag;
reg [58:0] p_native_result_tag=0;integer t_native_result_tag=0;
wire [17:0] o0_native_result_token;
wire [17:0] o1_native_result_token;
reg [17:0] p_native_result_token=0;integer t_native_result_token=0;
wire o0_native_result_v;
wire o1_native_result_v;
reg p_native_result_v=0;integer t_native_result_v=0;
wire [31:0] o0_native_result_value;
wire [31:0] o1_native_result_value;
reg [31:0] p_native_result_value=0;integer t_native_result_value=0;
reg [15:0] step_client_tag=0;
reg step_issue_v=0;
reg [17:0] step_pos=0;
reg [15:0] step_retire_client_tag=0;
reg step_retire_cq=0;
reg [17:0] step_retire_pos=0;
reg [7:0] step_retire_slot=0;
reg [17:0] step_retire_token=0;
reg step_retire_v=0;
reg [7:0] step_slot=0;
reg [15:0] u_rank__u_control__begin_epoch=0;
wire o0_u_rank__u_control__ctrl_begin_available;
wire o1_u_rank__u_control__ctrl_begin_available;
reg p_u_rank__u_control__ctrl_begin_available=0;integer t_u_rank__u_control__ctrl_begin_available=0;
wire o0_u_rank__u_control__begin_cr;
wire o1_u_rank__u_control__begin_cr;
reg p_u_rank__u_control__begin_cr=0;integer t_u_rank__u_control__begin_cr=0;
reg u_rank__u_control__begin_v=0;
wire [15:0] o0_u_rank__u_control__boot8;
wire [15:0] o1_u_rank__u_control__boot8;
reg [15:0] p_u_rank__u_control__boot8=0;integer t_u_rank__u_control__boot8=0;
wire [79:0] o0_u_rank__u_control__kst8;
wire [79:0] o1_u_rank__u_control__kst8;
reg [79:0] p_u_rank__u_control__kst8=0;integer t_u_rank__u_control__kst8=0;
wire [7:0] o0_u_rank__peer_pending_ack;
wire [7:0] o1_u_rank__peer_pending_ack;
reg [7:0] p_u_rank__peer_pending_ack=0;integer t_u_rank__peer_pending_ack=0;
wire [127:0] o0_u_rank__peer_service_epoch;
wire [127:0] o1_u_rank__peer_service_epoch;
reg [127:0] p_u_rank__peer_service_epoch=0;integer t_u_rank__peer_service_epoch=0;
wire [7:0] o0_u_rank__peer_service_ready;
wire [7:0] o1_u_rank__peer_service_ready;
reg [7:0] p_u_rank__peer_service_ready=0;integer t_u_rank__peer_service_ready=0;
reg u_rank__u_control__startup_allowed=0;
wire [743:0] o0_u_rank__u_control__tk8;
wire [743:0] o1_u_rank__u_control__tk8;
reg [743:0] p_u_rank__u_control__tk8=0;integer t_u_rank__u_control__tk8=0;
wire o0_u_rank__u_control__cmd_cr;
wire o1_u_rank__u_control__cmd_cr;
reg p_u_rank__u_control__cmd_cr=0;integer t_u_rank__u_control__cmd_cr=0;
reg [181:0] u_rank__u_control__cmd_hc=0;
reg u_rank__u_control__cmd_v=0;
reg [92:0] u_rank__guarded_tk=0;
wire o0_u_rank__pending_advertised;
wire o1_u_rank__pending_advertised;
reg p_u_rank__pending_advertised=0;integer t_u_rank__pending_advertised=0;
wire [15:0] o0_u_rank__pending_epoch;
wire [15:0] o1_u_rank__pending_epoch;
reg [15:0] p_u_rank__pending_epoch=0;integer t_u_rank__pending_epoch=0;
wire o0_u_rank__u_control__u_packet__cr;
wire o1_u_rank__u_control__u_packet__cr;
reg p_u_rank__u_control__u_packet__cr=0;integer t_u_rank__u_control__u_packet__cr=0;
reg [511:0] u_rank__u_control__u_packet__cd=0;
reg u_rank__u_control__u_packet__cv=0;
wire [15:0] o0_u_rank__service_begin_epoch;
wire [15:0] o1_u_rank__service_begin_epoch;
reg [15:0] p_u_rank__service_begin_epoch=0;integer t_u_rank__service_begin_epoch=0;
wire o0_u_rank__service_begin_v;
wire o1_u_rank__service_begin_v;
reg p_u_rank__service_begin_v=0;integer t_u_rank__service_begin_v=0;
reg u_rank__u_control__u_packet__ctc=0;
wire [511:0] o0_u_rank__u_control__u_packet__ctd;
wire [511:0] o1_u_rank__u_control__u_packet__ctd;
reg [511:0] p_u_rank__u_control__u_packet__ctd=0;integer t_u_rank__u_control__u_packet__ctd=0;
wire o0_u_rank__u_control__u_packet__ct;
wire o1_u_rank__u_control__u_packet__ct;
reg p_u_rank__u_control__u_packet__ct=0;integer t_u_rank__u_control__u_packet__ct=0;
wire o0_u_rank__tx_cr;
wire o1_u_rank__tx_cr;
reg p_u_rank__tx_cr=0;integer t_u_rank__tx_cr=0;
reg [527:0] u_rank__tx_d=0;
reg u_rank__tx_v=0;
reg u_rank__program_rx_cr=0;
wire [527:0] o0_u_rank__program_rx_d;
wire [527:0] o1_u_rank__program_rx_d;
reg [527:0] p_u_rank__program_rx_d=0;integer t_u_rank__program_rx_d=0;
wire o0_u_rank__program_rx_v;
wire o1_u_rank__program_rx_v;
reg p_u_rank__program_rx_v=0;integer t_u_rank__program_rx_v=0;
wire o0_u_rank__raw_rx_cr;
wire o1_u_rank__raw_rx_cr;
reg p_u_rank__raw_rx_cr=0;integer t_u_rank__raw_rx_cr=0;
reg [527:0] u_rank__raw_rx_d=0;
reg u_rank__raw_rx_v=0;
reg u_rank__physical_tx_cr=0;
wire [527:0] o0_u_rank__physical_tx_d;
wire [527:0] o1_u_rank__physical_tx_d;
reg [527:0] p_u_rank__physical_tx_d=0;integer t_u_rank__physical_tx_d=0;
wire o0_u_rank__physical_tx_v;
wire o1_u_rank__physical_tx_v;
reg p_u_rank__physical_tx_v=0;integer t_u_rank__physical_tx_v=0;
qkd_hr_core_peer_ref_native ref_dut(.ck_core(ck_core),.program_epoch(program_epoch),.program_digest(program_digest),.package_abort(package_abort),.abort_drained(abort_drained),.token_epoch_valid(o0_token_epoch_valid),.token_epoch(o0_token_epoch),.native_kv_drained(native_kv_drained),.native_vm_drained(native_vm_drained),.native_collective_drained(native_collective_drained),.native_host_drained(native_host_drained),.service_ready(service_ready),.ingest_permission(o0_ingest_permission),.local_service_epoch(local_service_epoch),.die_id(die_id),.por_n(por_n),.pll_locked(pll_locked),.local_kst(local_kst),.program_ready(program_ready),.hc(o0_hc),.seen(o0_seen),.host_rst_n(host_rst_n),.slice_boot_done(slice_boot_done),.slice_boot_ok(slice_boot_ok),.service_faults(o0_service_faults),.native_admit_ready(native_admit_ready),.native_links_drained(native_links_drained),.native_link_reset_seen(native_link_reset_seen),.native_retrained(native_retrained),.peer_protocol_fault(o0_peer_protocol_fault),.dispatch_valid(o0_dispatch_valid),.dispatched(o0_dispatched),.cohort_tag(o0_cohort_tag),.cohort_gen(o0_cohort_gen),.accepted_ranks(o0_accepted_ranks),.participant_trace(o0_participant_trace),.participant_token(o0_participant_token),.participant_pos(o0_participant_pos),.engine_result_v(engine_result_v),.engine_result_tag(engine_result_tag),.engine_result_gen(engine_result_gen),.engine_result_done(engine_result_done),.engine_result_fault(engine_result_fault),.engine_result_cause(engine_result_cause),.engine_result_token(engine_result_token),.engine_result_value(engine_result_value),.engine_result_cycles(engine_result_cycles),.engine_result_cr(o0_engine_result_cr),.program_consensus(o0_program_consensus),.coordinator_fault(o0_coordinator_fault),.recovery_complete(o0_recovery_complete),.host_link_reset_req(o0_host_link_reset_req),.host_recovery_clear(o0_host_recovery_clear),.root_mux_fault(o0_root_mux_fault),.allocated_valid(o0_allocated_valid),.native_context_owned(native_context_owned),.u_rank__u_control__por_n(o0_u_rank__u_control__por_n),.u_rank__u_control__service_ready(u_rank__u_control__service_ready),.u_rank__peer_link_fault(o0_u_rank__peer_link_fault),.cancel_release_gen(o0_cancel_release_gen),.cancel_release_tag(o0_cancel_release_tag),.cancel_release_v(o0_cancel_release_v),.cancel_released(cancel_released),.certificate(certificate),.certificate_prefix(certificate_prefix),.certificate_v(certificate_v),.cq_client_tag(cq_client_tag),.cq_commit_v(cq_commit_v),.cq_pos(cq_pos),.cq_slot(cq_slot),.cq_token(cq_token),.native_request_cr(o0_native_request_cr),.native_request_gen(native_request_gen),.native_request_pos(native_request_pos),.native_request_tag(native_request_tag),.native_request_token(native_request_token),.native_request_trace(native_request_trace),.native_request_v(native_request_v),.native_result_cause(o0_native_result_cause),.native_result_cr(native_result_cr),.native_result_cycles(o0_native_result_cycles),.native_result_done(o0_native_result_done),.native_result_fault(o0_native_result_fault),.native_result_gen(o0_native_result_gen),.native_result_tag(o0_native_result_tag),.native_result_token(o0_native_result_token),.native_result_v(o0_native_result_v),.native_result_value(o0_native_result_value),.step_client_tag(step_client_tag),.step_issue_v(step_issue_v),.step_pos(step_pos),.step_retire_client_tag(step_retire_client_tag),.step_retire_cq(step_retire_cq),.step_retire_pos(step_retire_pos),.step_retire_slot(step_retire_slot),.step_retire_token(step_retire_token),.step_retire_v(step_retire_v),.step_slot(step_slot),.u_rank__u_control__begin_epoch(u_rank__u_control__begin_epoch),.u_rank__u_control__ctrl_begin_available(o0_u_rank__u_control__ctrl_begin_available),.u_rank__u_control__begin_cr(o0_u_rank__u_control__begin_cr),.u_rank__u_control__begin_v(u_rank__u_control__begin_v),.u_rank__u_control__boot8(o0_u_rank__u_control__boot8),.u_rank__u_control__kst8(o0_u_rank__u_control__kst8),.u_rank__peer_pending_ack(o0_u_rank__peer_pending_ack),.u_rank__peer_service_epoch(o0_u_rank__peer_service_epoch),.u_rank__peer_service_ready(o0_u_rank__peer_service_ready),.u_rank__u_control__startup_allowed(u_rank__u_control__startup_allowed),.u_rank__u_control__tk8(o0_u_rank__u_control__tk8),.u_rank__u_control__cmd_cr(o0_u_rank__u_control__cmd_cr),.u_rank__u_control__cmd_hc(u_rank__u_control__cmd_hc),.u_rank__u_control__cmd_v(u_rank__u_control__cmd_v),.u_rank__guarded_tk(u_rank__guarded_tk),.u_rank__pending_advertised(o0_u_rank__pending_advertised),.u_rank__pending_epoch(o0_u_rank__pending_epoch),.u_rank__u_control__u_packet__cr(o0_u_rank__u_control__u_packet__cr),.u_rank__u_control__u_packet__cd(u_rank__u_control__u_packet__cd),.u_rank__u_control__u_packet__cv(u_rank__u_control__u_packet__cv),.u_rank__service_begin_epoch(o0_u_rank__service_begin_epoch),.u_rank__service_begin_v(o0_u_rank__service_begin_v),.u_rank__u_control__u_packet__ctc(u_rank__u_control__u_packet__ctc),.u_rank__u_control__u_packet__ctd(o0_u_rank__u_control__u_packet__ctd),.u_rank__u_control__u_packet__ct(o0_u_rank__u_control__u_packet__ct),.u_rank__tx_cr(o0_u_rank__tx_cr),.u_rank__tx_d(u_rank__tx_d),.u_rank__tx_v(u_rank__tx_v),.u_rank__program_rx_cr(u_rank__program_rx_cr),.u_rank__program_rx_d(o0_u_rank__program_rx_d),.u_rank__program_rx_v(o0_u_rank__program_rx_v),.u_rank__raw_rx_cr(o0_u_rank__raw_rx_cr),.u_rank__raw_rx_d(u_rank__raw_rx_d),.u_rank__raw_rx_v(u_rank__raw_rx_v),.u_rank__physical_tx_cr(u_rank__physical_tx_cr),.u_rank__physical_tx_d(o0_u_rank__physical_tx_d),.u_rank__physical_tx_v(o0_u_rank__physical_tx_v));
qkd_hr_core_peer_n32 dut(.ck_core(ck_core),.program_epoch(program_epoch),.program_digest(program_digest),.package_abort(package_abort),.abort_drained(abort_drained),.token_epoch_valid(o1_token_epoch_valid),.token_epoch(o1_token_epoch),.native_kv_drained(native_kv_drained),.native_vm_drained(native_vm_drained),.native_collective_drained(native_collective_drained),.native_host_drained(native_host_drained),.service_ready(service_ready),.ingest_permission(o1_ingest_permission),.local_service_epoch(local_service_epoch),.die_id(die_id),.por_n(por_n),.pll_locked(pll_locked),.local_kst(local_kst),.program_ready(program_ready),.hc(o1_hc),.seen(o1_seen),.host_rst_n(host_rst_n),.slice_boot_done(slice_boot_done),.slice_boot_ok(slice_boot_ok),.service_faults(o1_service_faults),.native_admit_ready(native_admit_ready),.native_links_drained(native_links_drained),.native_link_reset_seen(native_link_reset_seen),.native_retrained(native_retrained),.peer_protocol_fault(o1_peer_protocol_fault),.dispatch_valid(o1_dispatch_valid),.dispatched(o1_dispatched),.cohort_tag(o1_cohort_tag),.cohort_gen(o1_cohort_gen),.accepted_ranks(o1_accepted_ranks),.participant_trace(o1_participant_trace),.participant_token(o1_participant_token),.participant_pos(o1_participant_pos),.engine_result_v(engine_result_v),.engine_result_tag(engine_result_tag),.engine_result_gen(engine_result_gen),.engine_result_done(engine_result_done),.engine_result_fault(engine_result_fault),.engine_result_cause(engine_result_cause),.engine_result_token(engine_result_token),.engine_result_value(engine_result_value),.engine_result_cycles(engine_result_cycles),.engine_result_cr(o1_engine_result_cr),.program_consensus(o1_program_consensus),.coordinator_fault(o1_coordinator_fault),.recovery_complete(o1_recovery_complete),.host_link_reset_req(o1_host_link_reset_req),.host_recovery_clear(o1_host_recovery_clear),.root_mux_fault(o1_root_mux_fault),.allocated_valid(o1_allocated_valid),.native_context_owned(native_context_owned),.u_rank__u_control__por_n(o1_u_rank__u_control__por_n),.u_rank__u_control__service_ready(u_rank__u_control__service_ready),.u_rank__peer_link_fault(o1_u_rank__peer_link_fault),.cancel_release_gen(o1_cancel_release_gen),.cancel_release_tag(o1_cancel_release_tag),.cancel_release_v(o1_cancel_release_v),.cancel_released(cancel_released),.certificate(certificate),.certificate_prefix(certificate_prefix),.certificate_v(certificate_v),.cq_client_tag(cq_client_tag),.cq_commit_v(cq_commit_v),.cq_pos(cq_pos),.cq_slot(cq_slot),.cq_token(cq_token),.native_request_cr(o1_native_request_cr),.native_request_gen(native_request_gen),.native_request_pos(native_request_pos),.native_request_tag(native_request_tag),.native_request_token(native_request_token),.native_request_trace(native_request_trace),.native_request_v(native_request_v),.native_result_cause(o1_native_result_cause),.native_result_cr(native_result_cr),.native_result_cycles(o1_native_result_cycles),.native_result_done(o1_native_result_done),.native_result_fault(o1_native_result_fault),.native_result_gen(o1_native_result_gen),.native_result_tag(o1_native_result_tag),.native_result_token(o1_native_result_token),.native_result_v(o1_native_result_v),.native_result_value(o1_native_result_value),.step_client_tag(step_client_tag),.step_issue_v(step_issue_v),.step_pos(step_pos),.step_retire_client_tag(step_retire_client_tag),.step_retire_cq(step_retire_cq),.step_retire_pos(step_retire_pos),.step_retire_slot(step_retire_slot),.step_retire_token(step_retire_token),.step_retire_v(step_retire_v),.step_slot(step_slot),.u_rank__u_control__begin_epoch(u_rank__u_control__begin_epoch),.u_rank__u_control__ctrl_begin_available(o1_u_rank__u_control__ctrl_begin_available),.u_rank__u_control__begin_cr(o1_u_rank__u_control__begin_cr),.u_rank__u_control__begin_v(u_rank__u_control__begin_v),.u_rank__u_control__boot8(o1_u_rank__u_control__boot8),.u_rank__u_control__kst8(o1_u_rank__u_control__kst8),.u_rank__peer_pending_ack(o1_u_rank__peer_pending_ack),.u_rank__peer_service_epoch(o1_u_rank__peer_service_epoch),.u_rank__peer_service_ready(o1_u_rank__peer_service_ready),.u_rank__u_control__startup_allowed(u_rank__u_control__startup_allowed),.u_rank__u_control__tk8(o1_u_rank__u_control__tk8),.u_rank__u_control__cmd_cr(o1_u_rank__u_control__cmd_cr),.u_rank__u_control__cmd_hc(u_rank__u_control__cmd_hc),.u_rank__u_control__cmd_v(u_rank__u_control__cmd_v),.u_rank__guarded_tk(u_rank__guarded_tk),.u_rank__pending_advertised(o1_u_rank__pending_advertised),.u_rank__pending_epoch(o1_u_rank__pending_epoch),.u_rank__u_control__u_packet__cr(o1_u_rank__u_control__u_packet__cr),.u_rank__u_control__u_packet__cd(u_rank__u_control__u_packet__cd),.u_rank__u_control__u_packet__cv(u_rank__u_control__u_packet__cv),.u_rank__service_begin_epoch(o1_u_rank__service_begin_epoch),.u_rank__service_begin_v(o1_u_rank__service_begin_v),.u_rank__u_control__u_packet__ctc(u_rank__u_control__u_packet__ctc),.u_rank__u_control__u_packet__ctd(o1_u_rank__u_control__u_packet__ctd),.u_rank__u_control__u_packet__ct(o1_u_rank__u_control__u_packet__ct),.u_rank__tx_cr(o1_u_rank__tx_cr),.u_rank__tx_d(u_rank__tx_d),.u_rank__tx_v(u_rank__tx_v),.u_rank__program_rx_cr(u_rank__program_rx_cr),.u_rank__program_rx_d(o1_u_rank__program_rx_d),.u_rank__program_rx_v(o1_u_rank__program_rx_v),.u_rank__raw_rx_cr(o1_u_rank__raw_rx_cr),.u_rank__raw_rx_d(u_rank__raw_rx_d),.u_rank__raw_rx_v(u_rank__raw_rx_v),.u_rank__physical_tx_cr(u_rank__physical_tx_cr),.u_rank__physical_tx_d(o1_u_rank__physical_tx_d),.u_rank__physical_tx_v(o1_u_rank__physical_tx_v));
integer cycle,checks=0,toggled=0;
initial begin for(cycle=0;cycle<100000;cycle=cycle+1)begin @(negedge ck_core);
program_epoch[0 +: 16]=16'($urandom());
program_digest[0 +: 32]=32'($urandom());
program_digest[32 +: 32]=32'($urandom());
package_abort=1'($urandom());
abort_drained[0 +: 4]=4'($urandom());
native_kv_drained=1'($urandom());
native_vm_drained=1'($urandom());
native_collective_drained=1'($urandom());
native_host_drained=1'($urandom());
service_ready=1'($urandom());
local_service_epoch[0 +: 16]=16'($urandom());
die_id[0 +: 3]=3'($urandom());
por_n=1'($urandom());
pll_locked=1'($urandom());
local_kst[0 +: 10]=10'($urandom());
program_ready=1'($urandom());
host_rst_n=1'($urandom());
slice_boot_done[0 +: 32]=32'($urandom());
slice_boot_done[32 +: 32]=32'($urandom());
slice_boot_done[64 +: 32]=32'($urandom());
slice_boot_done[96 +: 32]=32'($urandom());
slice_boot_ok[0 +: 32]=32'($urandom());
slice_boot_ok[32 +: 32]=32'($urandom());
slice_boot_ok[64 +: 32]=32'($urandom());
slice_boot_ok[96 +: 32]=32'($urandom());
native_admit_ready=1'($urandom());
native_links_drained=1'($urandom());
native_link_reset_seen=1'($urandom());
native_retrained=1'($urandom());
engine_result_v=1'($urandom());
engine_result_tag[0 +: 32]=32'($urandom());
engine_result_tag[32 +: 27]=27'($urandom());
engine_result_gen[0 +: 2]=2'($urandom());
engine_result_done=1'($urandom());
engine_result_fault=1'($urandom());
engine_result_cause[0 +: 4]=4'($urandom());
engine_result_token[0 +: 18]=18'($urandom());
engine_result_value[0 +: 32]=32'($urandom());
engine_result_cycles[0 +: 32]=32'($urandom());
native_context_owned=1'($urandom());
u_rank__u_control__service_ready=1'($urandom());
cancel_released=1'($urandom());
certificate[0 +: 32]=32'($urandom());
certificate[32 +: 32]=32'($urandom());
certificate[64 +: 2]=2'($urandom());
certificate_prefix[0 +: 32]=32'($urandom());
certificate_v=1'($urandom());
cq_client_tag[0 +: 16]=16'($urandom());
cq_commit_v=1'($urandom());
cq_pos[0 +: 18]=18'($urandom());
cq_slot[0 +: 8]=8'($urandom());
cq_token[0 +: 18]=18'($urandom());
native_request_gen[0 +: 2]=2'($urandom());
native_request_pos[0 +: 18]=18'($urandom());
native_request_tag[0 +: 32]=32'($urandom());
native_request_tag[32 +: 27]=27'($urandom());
native_request_token[0 +: 18]=18'($urandom());
native_request_trace[0 +: 32]=32'($urandom());
native_request_v=1'($urandom());
native_result_cr=1'($urandom());
step_client_tag[0 +: 16]=16'($urandom());
step_issue_v=1'($urandom());
step_pos[0 +: 18]=18'($urandom());
step_retire_client_tag[0 +: 16]=16'($urandom());
step_retire_cq=1'($urandom());
step_retire_pos[0 +: 18]=18'($urandom());
step_retire_slot[0 +: 8]=8'($urandom());
step_retire_token[0 +: 18]=18'($urandom());
step_retire_v=1'($urandom());
step_slot[0 +: 8]=8'($urandom());
u_rank__u_control__begin_epoch[0 +: 16]=16'($urandom());
u_rank__u_control__begin_v=1'($urandom());
u_rank__u_control__startup_allowed=1'($urandom());
u_rank__u_control__cmd_hc[0 +: 32]=32'($urandom());
u_rank__u_control__cmd_hc[32 +: 32]=32'($urandom());
u_rank__u_control__cmd_hc[64 +: 32]=32'($urandom());
u_rank__u_control__cmd_hc[96 +: 32]=32'($urandom());
u_rank__u_control__cmd_hc[128 +: 32]=32'($urandom());
u_rank__u_control__cmd_hc[160 +: 22]=22'($urandom());
u_rank__u_control__cmd_v=1'($urandom());
u_rank__guarded_tk[0 +: 32]=32'($urandom());
u_rank__guarded_tk[32 +: 32]=32'($urandom());
u_rank__guarded_tk[64 +: 29]=29'($urandom());
u_rank__u_control__u_packet__cd[0 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[32 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[64 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[96 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[128 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[160 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[192 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[224 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[256 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[288 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[320 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[352 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[384 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[416 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[448 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cd[480 +: 32]=32'($urandom());
u_rank__u_control__u_packet__cv=1'($urandom());
u_rank__u_control__u_packet__ctc=1'($urandom());
u_rank__tx_d[0 +: 32]=32'($urandom());
u_rank__tx_d[32 +: 32]=32'($urandom());
u_rank__tx_d[64 +: 32]=32'($urandom());
u_rank__tx_d[96 +: 32]=32'($urandom());
u_rank__tx_d[128 +: 32]=32'($urandom());
u_rank__tx_d[160 +: 32]=32'($urandom());
u_rank__tx_d[192 +: 32]=32'($urandom());
u_rank__tx_d[224 +: 32]=32'($urandom());
u_rank__tx_d[256 +: 32]=32'($urandom());
u_rank__tx_d[288 +: 32]=32'($urandom());
u_rank__tx_d[320 +: 32]=32'($urandom());
u_rank__tx_d[352 +: 32]=32'($urandom());
u_rank__tx_d[384 +: 32]=32'($urandom());
u_rank__tx_d[416 +: 32]=32'($urandom());
u_rank__tx_d[448 +: 32]=32'($urandom());
u_rank__tx_d[480 +: 32]=32'($urandom());
u_rank__tx_d[512 +: 16]=16'($urandom());
u_rank__tx_v=1'($urandom());
u_rank__program_rx_cr=1'($urandom());
u_rank__raw_rx_d[0 +: 32]=32'($urandom());
u_rank__raw_rx_d[32 +: 32]=32'($urandom());
u_rank__raw_rx_d[64 +: 32]=32'($urandom());
u_rank__raw_rx_d[96 +: 32]=32'($urandom());
u_rank__raw_rx_d[128 +: 32]=32'($urandom());
u_rank__raw_rx_d[160 +: 32]=32'($urandom());
u_rank__raw_rx_d[192 +: 32]=32'($urandom());
u_rank__raw_rx_d[224 +: 32]=32'($urandom());
u_rank__raw_rx_d[256 +: 32]=32'($urandom());
u_rank__raw_rx_d[288 +: 32]=32'($urandom());
u_rank__raw_rx_d[320 +: 32]=32'($urandom());
u_rank__raw_rx_d[352 +: 32]=32'($urandom());
u_rank__raw_rx_d[384 +: 32]=32'($urandom());
u_rank__raw_rx_d[416 +: 32]=32'($urandom());
u_rank__raw_rx_d[448 +: 32]=32'($urandom());
u_rank__raw_rx_d[480 +: 32]=32'($urandom());
u_rank__raw_rx_d[512 +: 16]=16'($urandom());
u_rank__raw_rx_v=1'($urandom());
u_rank__physical_tx_cr=1'($urandom());
por_n=(cycle%256>=16);host_rst_n=por_n;die_id=0;package_abort=0;pll_locked=1;
@(posedge ck_core);#1;if(cycle>=16)begin
if(o0_token_epoch_valid!==o1_token_epoch_valid)begin $display("PEER_NATIVE FAIL edge=%0d port=token_epoch_valid",cycle);$fatal;end
if(o0_token_epoch!==o1_token_epoch)begin $display("PEER_NATIVE FAIL edge=%0d port=token_epoch",cycle);$fatal;end
if(o0_ingest_permission!==o1_ingest_permission)begin $display("PEER_NATIVE FAIL edge=%0d port=ingest_permission",cycle);$fatal;end
if(o0_hc!==o1_hc)begin $display("PEER_NATIVE FAIL edge=%0d port=hc",cycle);$fatal;end
if(o0_seen!==o1_seen)begin $display("PEER_NATIVE FAIL edge=%0d port=seen",cycle);$fatal;end
if(o0_service_faults!==o1_service_faults)begin $display("PEER_NATIVE FAIL edge=%0d port=service_faults",cycle);$fatal;end
if(o0_peer_protocol_fault!==o1_peer_protocol_fault)begin $display("PEER_NATIVE FAIL edge=%0d port=peer_protocol_fault",cycle);$fatal;end
if(o0_dispatch_valid!==o1_dispatch_valid)begin $display("PEER_NATIVE FAIL edge=%0d port=dispatch_valid",cycle);$fatal;end
if(o0_dispatched!==o1_dispatched)begin $display("PEER_NATIVE FAIL edge=%0d port=dispatched",cycle);$fatal;end
if(o0_cohort_tag!==o1_cohort_tag)begin $display("PEER_NATIVE FAIL edge=%0d port=cohort_tag",cycle);$fatal;end
if(o0_cohort_gen!==o1_cohort_gen)begin $display("PEER_NATIVE FAIL edge=%0d port=cohort_gen",cycle);$fatal;end
if(o0_accepted_ranks!==o1_accepted_ranks)begin $display("PEER_NATIVE FAIL edge=%0d port=accepted_ranks",cycle);$fatal;end
if(o0_participant_trace!==o1_participant_trace)begin $display("PEER_NATIVE FAIL edge=%0d port=participant_trace",cycle);$fatal;end
if(o0_participant_token!==o1_participant_token)begin $display("PEER_NATIVE FAIL edge=%0d port=participant_token",cycle);$fatal;end
if(o0_participant_pos!==o1_participant_pos)begin $display("PEER_NATIVE FAIL edge=%0d port=participant_pos",cycle);$fatal;end
if(o0_engine_result_cr!==o1_engine_result_cr)begin $display("PEER_NATIVE FAIL edge=%0d port=engine_result_cr",cycle);$fatal;end
if(o0_program_consensus!==o1_program_consensus)begin $display("PEER_NATIVE FAIL edge=%0d port=program_consensus",cycle);$fatal;end
if(o0_coordinator_fault!==o1_coordinator_fault)begin $display("PEER_NATIVE FAIL edge=%0d port=coordinator_fault",cycle);$fatal;end
if(o0_recovery_complete!==o1_recovery_complete)begin $display("PEER_NATIVE FAIL edge=%0d port=recovery_complete",cycle);$fatal;end
if(o0_host_link_reset_req!==o1_host_link_reset_req)begin $display("PEER_NATIVE FAIL edge=%0d port=host_link_reset_req",cycle);$fatal;end
if(o0_host_recovery_clear!==o1_host_recovery_clear)begin $display("PEER_NATIVE FAIL edge=%0d port=host_recovery_clear",cycle);$fatal;end
if(o0_root_mux_fault!==o1_root_mux_fault)begin $display("PEER_NATIVE FAIL edge=%0d port=root_mux_fault",cycle);$fatal;end
if(o0_allocated_valid!==o1_allocated_valid)begin $display("PEER_NATIVE FAIL edge=%0d port=allocated_valid",cycle);$fatal;end
if(o0_u_rank__u_control__por_n!==o1_u_rank__u_control__por_n)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__por_n",cycle);$fatal;end
if(o0_u_rank__peer_link_fault!==o1_u_rank__peer_link_fault)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__peer_link_fault",cycle);$fatal;end
if(o0_cancel_release_gen!==o1_cancel_release_gen)begin $display("PEER_NATIVE FAIL edge=%0d port=cancel_release_gen",cycle);$fatal;end
if(o0_cancel_release_tag!==o1_cancel_release_tag)begin $display("PEER_NATIVE FAIL edge=%0d port=cancel_release_tag",cycle);$fatal;end
if(o0_cancel_release_v!==o1_cancel_release_v)begin $display("PEER_NATIVE FAIL edge=%0d port=cancel_release_v",cycle);$fatal;end
if(o0_native_request_cr!==o1_native_request_cr)begin $display("PEER_NATIVE FAIL edge=%0d port=native_request_cr",cycle);$fatal;end
if(o0_native_result_cause!==o1_native_result_cause)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_cause",cycle);$fatal;end
if(o0_native_result_cycles!==o1_native_result_cycles)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_cycles",cycle);$fatal;end
if(o0_native_result_done!==o1_native_result_done)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_done",cycle);$fatal;end
if(o0_native_result_fault!==o1_native_result_fault)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_fault",cycle);$fatal;end
if(o0_native_result_gen!==o1_native_result_gen)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_gen",cycle);$fatal;end
if(o0_native_result_tag!==o1_native_result_tag)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_tag",cycle);$fatal;end
if(o0_native_result_token!==o1_native_result_token)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_token",cycle);$fatal;end
if(o0_native_result_v!==o1_native_result_v)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_v",cycle);$fatal;end
if(o0_native_result_value!==o1_native_result_value)begin $display("PEER_NATIVE FAIL edge=%0d port=native_result_value",cycle);$fatal;end
if(o0_u_rank__u_control__ctrl_begin_available!==o1_u_rank__u_control__ctrl_begin_available)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__ctrl_begin_available",cycle);$fatal;end
if(o0_u_rank__u_control__begin_cr!==o1_u_rank__u_control__begin_cr)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__begin_cr",cycle);$fatal;end
if(o0_u_rank__u_control__boot8!==o1_u_rank__u_control__boot8)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__boot8",cycle);$fatal;end
if(o0_u_rank__u_control__kst8!==o1_u_rank__u_control__kst8)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__kst8",cycle);$fatal;end
if(o0_u_rank__peer_pending_ack!==o1_u_rank__peer_pending_ack)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__peer_pending_ack",cycle);$fatal;end
if(o0_u_rank__peer_service_epoch!==o1_u_rank__peer_service_epoch)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__peer_service_epoch",cycle);$fatal;end
if(o0_u_rank__peer_service_ready!==o1_u_rank__peer_service_ready)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__peer_service_ready",cycle);$fatal;end
if(o0_u_rank__u_control__tk8!==o1_u_rank__u_control__tk8)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__tk8",cycle);$fatal;end
if(o0_u_rank__u_control__cmd_cr!==o1_u_rank__u_control__cmd_cr)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__cmd_cr",cycle);$fatal;end
if(o0_u_rank__pending_advertised!==o1_u_rank__pending_advertised)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__pending_advertised",cycle);$fatal;end
if(o0_u_rank__pending_epoch!==o1_u_rank__pending_epoch)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__pending_epoch",cycle);$fatal;end
if(o0_u_rank__u_control__u_packet__cr!==o1_u_rank__u_control__u_packet__cr)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__u_packet__cr",cycle);$fatal;end
if(o0_u_rank__service_begin_epoch!==o1_u_rank__service_begin_epoch)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__service_begin_epoch",cycle);$fatal;end
if(o0_u_rank__service_begin_v!==o1_u_rank__service_begin_v)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__service_begin_v",cycle);$fatal;end
if(o0_u_rank__u_control__u_packet__ct&&o0_u_rank__u_control__u_packet__ctd!==o1_u_rank__u_control__u_packet__ctd)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__u_packet__ctd",cycle);$fatal;end
if(o0_u_rank__u_control__u_packet__ct!==o1_u_rank__u_control__u_packet__ct)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__u_control__u_packet__ct",cycle);$fatal;end
if(o0_u_rank__tx_cr!==o1_u_rank__tx_cr)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__tx_cr",cycle);$fatal;end
if(o0_u_rank__program_rx_v&&o0_u_rank__program_rx_d!==o1_u_rank__program_rx_d)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__program_rx_d",cycle);$fatal;end
if(o0_u_rank__program_rx_v!==o1_u_rank__program_rx_v)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__program_rx_v",cycle);$fatal;end
if(o0_u_rank__raw_rx_cr!==o1_u_rank__raw_rx_cr)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__raw_rx_cr",cycle);$fatal;end
if(o0_u_rank__physical_tx_v&&o0_u_rank__physical_tx_d!==o1_u_rank__physical_tx_d)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__physical_tx_d",cycle);$fatal;end
if(o0_u_rank__physical_tx_v!==o1_u_rank__physical_tx_v)begin $display("PEER_NATIVE FAIL edge=%0d port=u_rank__physical_tx_v",cycle);$fatal;end
if(p_token_epoch_valid!==o0_token_epoch_valid)t_token_epoch_valid=t_token_epoch_valid+1;p_token_epoch_valid=o0_token_epoch_valid;
if(p_token_epoch!==o0_token_epoch)t_token_epoch=t_token_epoch+1;p_token_epoch=o0_token_epoch;
if(p_ingest_permission!==o0_ingest_permission)t_ingest_permission=t_ingest_permission+1;p_ingest_permission=o0_ingest_permission;
if(p_hc!==o0_hc)t_hc=t_hc+1;p_hc=o0_hc;
if(p_seen!==o0_seen)t_seen=t_seen+1;p_seen=o0_seen;
if(p_service_faults!==o0_service_faults)t_service_faults=t_service_faults+1;p_service_faults=o0_service_faults;
if(p_peer_protocol_fault!==o0_peer_protocol_fault)t_peer_protocol_fault=t_peer_protocol_fault+1;p_peer_protocol_fault=o0_peer_protocol_fault;
if(p_dispatch_valid!==o0_dispatch_valid)t_dispatch_valid=t_dispatch_valid+1;p_dispatch_valid=o0_dispatch_valid;
if(p_dispatched!==o0_dispatched)t_dispatched=t_dispatched+1;p_dispatched=o0_dispatched;
if(p_cohort_tag!==o0_cohort_tag)t_cohort_tag=t_cohort_tag+1;p_cohort_tag=o0_cohort_tag;
if(p_cohort_gen!==o0_cohort_gen)t_cohort_gen=t_cohort_gen+1;p_cohort_gen=o0_cohort_gen;
if(p_accepted_ranks!==o0_accepted_ranks)t_accepted_ranks=t_accepted_ranks+1;p_accepted_ranks=o0_accepted_ranks;
if(p_participant_trace!==o0_participant_trace)t_participant_trace=t_participant_trace+1;p_participant_trace=o0_participant_trace;
if(p_participant_token!==o0_participant_token)t_participant_token=t_participant_token+1;p_participant_token=o0_participant_token;
if(p_participant_pos!==o0_participant_pos)t_participant_pos=t_participant_pos+1;p_participant_pos=o0_participant_pos;
if(p_engine_result_cr!==o0_engine_result_cr)t_engine_result_cr=t_engine_result_cr+1;p_engine_result_cr=o0_engine_result_cr;
if(p_program_consensus!==o0_program_consensus)t_program_consensus=t_program_consensus+1;p_program_consensus=o0_program_consensus;
if(p_coordinator_fault!==o0_coordinator_fault)t_coordinator_fault=t_coordinator_fault+1;p_coordinator_fault=o0_coordinator_fault;
if(p_recovery_complete!==o0_recovery_complete)t_recovery_complete=t_recovery_complete+1;p_recovery_complete=o0_recovery_complete;
if(p_host_link_reset_req!==o0_host_link_reset_req)t_host_link_reset_req=t_host_link_reset_req+1;p_host_link_reset_req=o0_host_link_reset_req;
if(p_host_recovery_clear!==o0_host_recovery_clear)t_host_recovery_clear=t_host_recovery_clear+1;p_host_recovery_clear=o0_host_recovery_clear;
if(p_root_mux_fault!==o0_root_mux_fault)t_root_mux_fault=t_root_mux_fault+1;p_root_mux_fault=o0_root_mux_fault;
if(p_allocated_valid!==o0_allocated_valid)t_allocated_valid=t_allocated_valid+1;p_allocated_valid=o0_allocated_valid;
if(p_u_rank__u_control__por_n!==o0_u_rank__u_control__por_n)t_u_rank__u_control__por_n=t_u_rank__u_control__por_n+1;p_u_rank__u_control__por_n=o0_u_rank__u_control__por_n;
if(p_u_rank__peer_link_fault!==o0_u_rank__peer_link_fault)t_u_rank__peer_link_fault=t_u_rank__peer_link_fault+1;p_u_rank__peer_link_fault=o0_u_rank__peer_link_fault;
if(p_cancel_release_gen!==o0_cancel_release_gen)t_cancel_release_gen=t_cancel_release_gen+1;p_cancel_release_gen=o0_cancel_release_gen;
if(p_cancel_release_tag!==o0_cancel_release_tag)t_cancel_release_tag=t_cancel_release_tag+1;p_cancel_release_tag=o0_cancel_release_tag;
if(p_cancel_release_v!==o0_cancel_release_v)t_cancel_release_v=t_cancel_release_v+1;p_cancel_release_v=o0_cancel_release_v;
if(p_native_request_cr!==o0_native_request_cr)t_native_request_cr=t_native_request_cr+1;p_native_request_cr=o0_native_request_cr;
if(p_native_result_cause!==o0_native_result_cause)t_native_result_cause=t_native_result_cause+1;p_native_result_cause=o0_native_result_cause;
if(p_native_result_cycles!==o0_native_result_cycles)t_native_result_cycles=t_native_result_cycles+1;p_native_result_cycles=o0_native_result_cycles;
if(p_native_result_done!==o0_native_result_done)t_native_result_done=t_native_result_done+1;p_native_result_done=o0_native_result_done;
if(p_native_result_fault!==o0_native_result_fault)t_native_result_fault=t_native_result_fault+1;p_native_result_fault=o0_native_result_fault;
if(p_native_result_gen!==o0_native_result_gen)t_native_result_gen=t_native_result_gen+1;p_native_result_gen=o0_native_result_gen;
if(p_native_result_tag!==o0_native_result_tag)t_native_result_tag=t_native_result_tag+1;p_native_result_tag=o0_native_result_tag;
if(p_native_result_token!==o0_native_result_token)t_native_result_token=t_native_result_token+1;p_native_result_token=o0_native_result_token;
if(p_native_result_v!==o0_native_result_v)t_native_result_v=t_native_result_v+1;p_native_result_v=o0_native_result_v;
if(p_native_result_value!==o0_native_result_value)t_native_result_value=t_native_result_value+1;p_native_result_value=o0_native_result_value;
if(p_u_rank__u_control__ctrl_begin_available!==o0_u_rank__u_control__ctrl_begin_available)t_u_rank__u_control__ctrl_begin_available=t_u_rank__u_control__ctrl_begin_available+1;p_u_rank__u_control__ctrl_begin_available=o0_u_rank__u_control__ctrl_begin_available;
if(p_u_rank__u_control__begin_cr!==o0_u_rank__u_control__begin_cr)t_u_rank__u_control__begin_cr=t_u_rank__u_control__begin_cr+1;p_u_rank__u_control__begin_cr=o0_u_rank__u_control__begin_cr;
if(p_u_rank__u_control__boot8!==o0_u_rank__u_control__boot8)t_u_rank__u_control__boot8=t_u_rank__u_control__boot8+1;p_u_rank__u_control__boot8=o0_u_rank__u_control__boot8;
if(p_u_rank__u_control__kst8!==o0_u_rank__u_control__kst8)t_u_rank__u_control__kst8=t_u_rank__u_control__kst8+1;p_u_rank__u_control__kst8=o0_u_rank__u_control__kst8;
if(p_u_rank__peer_pending_ack!==o0_u_rank__peer_pending_ack)t_u_rank__peer_pending_ack=t_u_rank__peer_pending_ack+1;p_u_rank__peer_pending_ack=o0_u_rank__peer_pending_ack;
if(p_u_rank__peer_service_epoch!==o0_u_rank__peer_service_epoch)t_u_rank__peer_service_epoch=t_u_rank__peer_service_epoch+1;p_u_rank__peer_service_epoch=o0_u_rank__peer_service_epoch;
if(p_u_rank__peer_service_ready!==o0_u_rank__peer_service_ready)t_u_rank__peer_service_ready=t_u_rank__peer_service_ready+1;p_u_rank__peer_service_ready=o0_u_rank__peer_service_ready;
if(p_u_rank__u_control__tk8!==o0_u_rank__u_control__tk8)t_u_rank__u_control__tk8=t_u_rank__u_control__tk8+1;p_u_rank__u_control__tk8=o0_u_rank__u_control__tk8;
if(p_u_rank__u_control__cmd_cr!==o0_u_rank__u_control__cmd_cr)t_u_rank__u_control__cmd_cr=t_u_rank__u_control__cmd_cr+1;p_u_rank__u_control__cmd_cr=o0_u_rank__u_control__cmd_cr;
if(p_u_rank__pending_advertised!==o0_u_rank__pending_advertised)t_u_rank__pending_advertised=t_u_rank__pending_advertised+1;p_u_rank__pending_advertised=o0_u_rank__pending_advertised;
if(p_u_rank__pending_epoch!==o0_u_rank__pending_epoch)t_u_rank__pending_epoch=t_u_rank__pending_epoch+1;p_u_rank__pending_epoch=o0_u_rank__pending_epoch;
if(p_u_rank__u_control__u_packet__cr!==o0_u_rank__u_control__u_packet__cr)t_u_rank__u_control__u_packet__cr=t_u_rank__u_control__u_packet__cr+1;p_u_rank__u_control__u_packet__cr=o0_u_rank__u_control__u_packet__cr;
if(p_u_rank__service_begin_epoch!==o0_u_rank__service_begin_epoch)t_u_rank__service_begin_epoch=t_u_rank__service_begin_epoch+1;p_u_rank__service_begin_epoch=o0_u_rank__service_begin_epoch;
if(p_u_rank__service_begin_v!==o0_u_rank__service_begin_v)t_u_rank__service_begin_v=t_u_rank__service_begin_v+1;p_u_rank__service_begin_v=o0_u_rank__service_begin_v;
if(p_u_rank__u_control__u_packet__ctd!==o0_u_rank__u_control__u_packet__ctd)t_u_rank__u_control__u_packet__ctd=t_u_rank__u_control__u_packet__ctd+1;p_u_rank__u_control__u_packet__ctd=o0_u_rank__u_control__u_packet__ctd;
if(p_u_rank__u_control__u_packet__ct!==o0_u_rank__u_control__u_packet__ct)t_u_rank__u_control__u_packet__ct=t_u_rank__u_control__u_packet__ct+1;p_u_rank__u_control__u_packet__ct=o0_u_rank__u_control__u_packet__ct;
if(p_u_rank__tx_cr!==o0_u_rank__tx_cr)t_u_rank__tx_cr=t_u_rank__tx_cr+1;p_u_rank__tx_cr=o0_u_rank__tx_cr;
if(p_u_rank__program_rx_d!==o0_u_rank__program_rx_d)t_u_rank__program_rx_d=t_u_rank__program_rx_d+1;p_u_rank__program_rx_d=o0_u_rank__program_rx_d;
if(p_u_rank__program_rx_v!==o0_u_rank__program_rx_v)t_u_rank__program_rx_v=t_u_rank__program_rx_v+1;p_u_rank__program_rx_v=o0_u_rank__program_rx_v;
if(p_u_rank__raw_rx_cr!==o0_u_rank__raw_rx_cr)t_u_rank__raw_rx_cr=t_u_rank__raw_rx_cr+1;p_u_rank__raw_rx_cr=o0_u_rank__raw_rx_cr;
if(p_u_rank__physical_tx_d!==o0_u_rank__physical_tx_d)t_u_rank__physical_tx_d=t_u_rank__physical_tx_d+1;p_u_rank__physical_tx_d=o0_u_rank__physical_tx_d;
if(p_u_rank__physical_tx_v!==o0_u_rank__physical_tx_v)t_u_rank__physical_tx_v=t_u_rank__physical_tx_v+1;p_u_rank__physical_tx_v=o0_u_rank__physical_tx_v;
checks=checks+1;end end
if(t_token_epoch_valid>0)toggled=toggled+1;
if(t_token_epoch>0)toggled=toggled+1;
if(t_ingest_permission>0)toggled=toggled+1;
if(t_hc>0)toggled=toggled+1;
if(t_seen>0)toggled=toggled+1;
if(t_service_faults>0)toggled=toggled+1;
if(t_peer_protocol_fault>0)toggled=toggled+1;
if(t_dispatch_valid>0)toggled=toggled+1;
if(t_dispatched>0)toggled=toggled+1;
if(t_cohort_tag>0)toggled=toggled+1;
if(t_cohort_gen>0)toggled=toggled+1;
if(t_accepted_ranks>0)toggled=toggled+1;
if(t_participant_trace>0)toggled=toggled+1;
if(t_participant_token>0)toggled=toggled+1;
if(t_participant_pos>0)toggled=toggled+1;
if(t_engine_result_cr>0)toggled=toggled+1;
if(t_program_consensus>0)toggled=toggled+1;
if(t_coordinator_fault>0)toggled=toggled+1;
if(t_recovery_complete>0)toggled=toggled+1;
if(t_host_link_reset_req>0)toggled=toggled+1;
if(t_host_recovery_clear>0)toggled=toggled+1;
if(t_root_mux_fault>0)toggled=toggled+1;
if(t_allocated_valid>0)toggled=toggled+1;
if(t_u_rank__u_control__por_n>0)toggled=toggled+1;
if(t_u_rank__peer_link_fault>0)toggled=toggled+1;
if(t_cancel_release_gen>0)toggled=toggled+1;
if(t_cancel_release_tag>0)toggled=toggled+1;
if(t_cancel_release_v>0)toggled=toggled+1;
if(t_native_request_cr>0)toggled=toggled+1;
if(t_native_result_cause>0)toggled=toggled+1;
if(t_native_result_cycles>0)toggled=toggled+1;
if(t_native_result_done>0)toggled=toggled+1;
if(t_native_result_fault>0)toggled=toggled+1;
if(t_native_result_gen>0)toggled=toggled+1;
if(t_native_result_tag>0)toggled=toggled+1;
if(t_native_result_token>0)toggled=toggled+1;
if(t_native_result_v>0)toggled=toggled+1;
if(t_native_result_value>0)toggled=toggled+1;
if(t_u_rank__u_control__ctrl_begin_available>0)toggled=toggled+1;
if(t_u_rank__u_control__begin_cr>0)toggled=toggled+1;
if(t_u_rank__u_control__boot8>0)toggled=toggled+1;
if(t_u_rank__u_control__kst8>0)toggled=toggled+1;
if(t_u_rank__peer_pending_ack>0)toggled=toggled+1;
if(t_u_rank__peer_service_epoch>0)toggled=toggled+1;
if(t_u_rank__peer_service_ready>0)toggled=toggled+1;
if(t_u_rank__u_control__tk8>0)toggled=toggled+1;
if(t_u_rank__u_control__cmd_cr>0)toggled=toggled+1;
if(t_u_rank__pending_advertised>0)toggled=toggled+1;
if(t_u_rank__pending_epoch>0)toggled=toggled+1;
if(t_u_rank__u_control__u_packet__cr>0)toggled=toggled+1;
if(t_u_rank__service_begin_epoch>0)toggled=toggled+1;
if(t_u_rank__service_begin_v>0)toggled=toggled+1;
if(t_u_rank__u_control__u_packet__ctd>0)toggled=toggled+1;
if(t_u_rank__u_control__u_packet__ct>0)toggled=toggled+1;
if(t_u_rank__tx_cr>0)toggled=toggled+1;
if(t_u_rank__program_rx_d>0)toggled=toggled+1;
if(t_u_rank__program_rx_v>0)toggled=toggled+1;
if(t_u_rank__raw_rx_cr>0)toggled=toggled+1;
if(t_u_rank__physical_tx_d>0)toggled=toggled+1;
if(t_u_rank__physical_tx_v>0)toggled=toggled+1;
if(toggled<8)begin $display("PEER_NATIVE FAIL coverage toggled=%0d",toggled);$fatal;end
$display("PEER_NATIVE PASS edges=%0d toggled_ports=%0d",checks,toggled);$finish;end endmodule
