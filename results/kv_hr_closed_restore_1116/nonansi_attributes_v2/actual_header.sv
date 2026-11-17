module qkd_host_root_admission_obsx_bo1_c45_hr4(host_upstream_quiet, d2d_boot_begin, static_setup_ready, mission_start, boot_pr, boot_image_target, boot_image_ready, boot_image_fault, boot_image_epoch, boot_image_digest, native_reserved, ownership_valid, host_launch_quiet, ck_phy, ck_pad, ck_phy_rx_w, ck_phy_rx_r, ck_phy_tx_w, ck_phy_tx_r, ck_peer, ck_program_rx
, ck_program_loader, ck_host, ck_csr, ck_rst, ck_ctl, ck_prompt, ck_rx, ck_tx, ck_axi, ck_ctrl, ck_hc, ck_qm_queue, ck_qm_ing_w, ck_qm_ing_r, ck_qm_credit, ck_qm_done_w, ck_qm_done_r, ck_qm_core, ck_qm_host, ck_qm_ingest, ck_qm_bank
, ck_qm_out, ck_map, ck_sum, ck_order, ck_dispatch, ck_retire, ck_bootbarrier, ck_fence_core, ck_fence_host, ck_guard, ck_native, abort_drained, token_epoch_valid, token_epoch, native_kv_drained, native_vm_drained, native_collective_drained, native_host_drained, native_collective_busy, native_kv_flush, die_id
, por_n, pll_locked, phy_up, phy_rx_v_w, phy_rx_v_e, phy_rx_flit, phy_tx_v, phy_tx_flit, link_up, transport_fault, link_physical_fault, crom_fault, local_tk, local_kst, ck_records, record_send_kind, record_witness_slot, record_rx_v, record_rx, record_tx_observed_v, record_tx
, execution_active, program_ready, program_epoch, program_digest, program_begin_v, host_rst_n, link_rst_n, hbm_rst_n, boot_go, die_rst_n, hb, hb_cr, est, chain_f, chain_c, chain_a, chain_fault_i, slice_ack, slice_boot_done, slice_boot_ok, slice_boot_fault
, ctrl_completion_fault, native_admit_ready, native_links_drained, native_link_reset_seen, native_retrained, ck_root_mux, ck_coordinator_codec, ck_coordinator_lifecycle, ck_coordinator_post, cohort_tag, cohort_gen, engine_result_v, engine_result_tag, engine_result_gen, engine_result_done, engine_result_fault, engine_result_cause, engine_result_token, engine_result_value, engine_result_cycles, host_link_reset_req
, host_recovery_clear, host_interface_idle, obs_dcal_adm_done, obs_dcal_cal_ready, obs_dcal_running, obs_dcal_layer, obs_d2d_recovery_cycles);
(* src = "actual selected host declaration" *)
  output [5:0] host_upstream_quiet;
(* src = "actual selected host declaration" *)
  output d2d_boot_begin;
(* src = "actual selected host declaration" *)
  input static_setup_ready;
(* src = "actual selected host declaration" *)
  input mission_start;
(* src = "actual selected host declaration" *)
  output [142:0] boot_pr;
(* src = "actual selected host declaration" *)
  output [3:0] boot_image_target;
(* src = "actual selected host declaration" *)
  output boot_image_ready;
(* src = "actual selected host declaration" *)
  output boot_image_fault;
(* src = "actual selected host declaration" *)
  output [15:0] boot_image_epoch;
(* src = "actual selected host declaration" *)
  output [63:0] boot_image_digest;
(* src = "actual selected host declaration" *)
  input native_reserved;
(* src = "actual selected host declaration" *)
  input ownership_valid;
(* src = "actual selected host declaration" *)
  output host_launch_quiet;
(* src = "actual selected host declaration" *)
  input [7:0] ck_phy;
(* src = "actual selected host declaration" *)
  input ck_pad;
(* src = "actual selected host declaration" *)
  input ck_phy_rx_w;
(* src = "actual selected host declaration" *)
  input ck_phy_rx_r;
(* src = "actual selected host declaration" *)
  input ck_phy_tx_w;
(* src = "actual selected host declaration" *)
  input ck_phy_tx_r;
(* src = "actual selected host declaration" *)
  input ck_peer;
(* src = "actual selected host declaration" *)
  input ck_program_rx;
(* src = "actual selected host declaration" *)
  input ck_program_loader;
(* src = "actual selected host declaration" *)
  input ck_host;
(* src = "actual selected host declaration" *)
  input ck_csr;
(* src = "actual selected host declaration" *)
  input ck_rst;
(* src = "actual selected host declaration" *)
  input ck_ctl;
(* src = "actual selected host declaration" *)
  input ck_prompt;
(* src = "actual selected host declaration" *)
  input ck_rx;
(* src = "actual selected host declaration" *)
  input ck_tx;
(* src = "actual selected host declaration" *)
  input ck_axi;
(* src = "actual selected host declaration" *)
  input ck_ctrl;
(* src = "actual selected host declaration" *)
  input ck_hc;
(* src = "actual selected host declaration" *)
  input ck_qm_queue;
(* src = "actual selected host declaration" *)
  input ck_qm_ing_w;
(* src = "actual selected host declaration" *)
  input ck_qm_ing_r;
(* src = "actual selected host declaration" *)
  input ck_qm_credit;
(* src = "actual selected host declaration" *)
  input ck_qm_done_w;
(* src = "actual selected host declaration" *)
  input ck_qm_done_r;
(* src = "actual selected host declaration" *)
  input ck_qm_core;
(* src = "actual selected host declaration" *)
  input ck_qm_host;
(* src = "actual selected host declaration" *)
  input ck_qm_ingest;
(* src = "actual selected host declaration" *)
  input [1:0] ck_qm_bank;
(* src = "actual selected host declaration" *)
  input ck_qm_out;
(* src = "actual selected host declaration" *)
  input ck_map;
(* src = "actual selected host declaration" *)
  input ck_sum;
(* src = "actual selected host declaration" *)
  input ck_order;
(* src = "actual selected host declaration" *)
  input ck_dispatch;
(* src = "actual selected host declaration" *)
  input ck_retire;
(* src = "actual selected host declaration" *)
  input ck_bootbarrier;
(* src = "actual selected host declaration" *)
  input ck_fence_core;
(* src = "actual selected host declaration" *)
  input ck_fence_host;
(* src = "actual selected host declaration" *)
  input ck_guard;
(* src = "actual selected host declaration" *)
  input ck_native;
(* src = "actual selected host declaration" *)
  input [3:0] abort_drained;
(* src = "actual selected host declaration" *)
  output token_epoch_valid;
(* src = "actual selected host declaration" *)
  output [15:0] token_epoch;
(* src = "actual selected host declaration" *)
  input native_kv_drained;
(* src = "actual selected host declaration" *)
  input native_vm_drained;
(* src = "actual selected host declaration" *)
  input native_collective_drained;
(* src = "actual selected host declaration" *)
  input native_host_drained;
(* src = "actual selected host declaration" *)
  input native_collective_busy;
(* src = "actual selected host declaration" *)
  input native_kv_flush;
(* src = "actual selected host declaration" *)
  input [2:0] die_id;
(* src = "actual selected host declaration" *)
  input por_n;
(* src = "actual selected host declaration" *)
  input pll_locked;
(* src = "actual selected host declaration" *)
  input phy_up;
(* src = "actual selected host declaration" *)
  input phy_rx_v_w;
(* src = "actual selected host declaration" *)
  input phy_rx_v_e;
(* src = "actual selected host declaration" *)
  input [1042:0] phy_rx_flit;
(* src = "actual selected host declaration" *)
  output phy_tx_v;
(* src = "actual selected host declaration" *)
  output [1042:0] phy_tx_flit;
(* src = "actual selected host declaration" *)
  input [1:0] link_up;
(* src = "actual selected host declaration" *)
  input [7:0] transport_fault;
(* src = "actual selected host declaration" *)
  input link_physical_fault;
(* src = "actual selected host declaration" *)
  input crom_fault;
(* src = "actual selected host declaration" *)
  input [92:0] local_tk;
(* src = "actual selected host declaration" *)
  input [9:0] local_kst;
(* src = "actual selected host declaration" *)
  input ck_records;
(* src = "actual selected host declaration" *)
  input [1:0] record_send_kind;
(* src = "actual selected host declaration" *)
  input record_witness_slot;
(* src = "actual selected host declaration" *)
  input record_rx_v;
(* src = "actual selected host declaration" *)
  input [547:0] record_rx;
(* src = "actual selected host declaration" *)
  output record_tx_observed_v;
(* src = "actual selected host declaration" *)
  output [547:0] record_tx;
(* src = "actual selected host declaration" *)
  input execution_active;
(* src = "actual selected host declaration" *)
  output program_ready;
(* src = "actual selected host declaration" *)
  output [15:0] program_epoch;
(* src = "actual selected host declaration" *)
  output [63:0] program_digest;
(* src = "actual selected host declaration" *)
  output program_begin_v;
(* src = "actual selected host declaration" *)
  output host_rst_n;
(* src = "actual selected host declaration" *)
  output link_rst_n;
(* src = "actual selected host declaration" *)
  output hbm_rst_n;
(* src = "actual selected host declaration" *)
  output boot_go;
(* src = "actual selected host declaration" *)
  output die_rst_n;
(* src = "actual selected host declaration" *)
  output [282:0] hb;
(* src = "actual selected host declaration" *)
  input hb_cr;
(* src = "actual selected host declaration" *)
  input [12:0] est;
(* src = "actual selected host declaration" *)
  output [1163:0] chain_f;
(* src = "actual selected host declaration" *)
  input [127:0] chain_c;
(* src = "actual selected host declaration" *)
  input [127:0] chain_a;
(* src = "actual selected host declaration" *)
  input [3:0] chain_fault_i;
(* src = "actual selected host declaration" *)
  input [127:0] slice_ack;
(* src = "actual selected host declaration" *)
  input [127:0] slice_boot_done;
(* src = "actual selected host declaration" *)
  input [127:0] slice_boot_ok;
(* src = "actual selected host declaration" *)
  input [127:0] slice_boot_fault;
(* src = "actual selected host declaration" *)
  input ctrl_completion_fault;
(* src = "actual selected host declaration" *)
  input native_admit_ready;
(* src = "actual selected host declaration" *)
  input native_links_drained;
(* src = "actual selected host declaration" *)
  input native_link_reset_seen;
(* src = "actual selected host declaration" *)
  input native_retrained;
(* src = "actual selected host declaration" *)
  input ck_root_mux;
(* src = "actual selected host declaration" *)
  input ck_coordinator_codec;
(* src = "actual selected host declaration" *)
  input ck_coordinator_lifecycle;
(* src = "actual selected host declaration" *)
  input ck_coordinator_post;
(* src = "actual selected host declaration" *)
  output [58:0] cohort_tag;
(* src = "actual selected host declaration" *)
  output [1:0] cohort_gen;
(* src = "actual selected host declaration" *)
  input engine_result_v;
(* src = "actual selected host declaration" *)
  input [58:0] engine_result_tag;
(* src = "actual selected host declaration" *)
  input [1:0] engine_result_gen;
(* src = "actual selected host declaration" *)
  input engine_result_done;
(* src = "actual selected host declaration" *)
  input engine_result_fault;
(* src = "actual selected host declaration" *)
  input [3:0] engine_result_cause;
(* src = "actual selected host declaration" *)
  input [17:0] engine_result_token;
(* src = "actual selected host declaration" *)
  input [31:0] engine_result_value;
(* src = "actual selected host declaration" *)
  input [31:0] engine_result_cycles;
(* src = "actual selected host declaration" *)
  output host_link_reset_req;
(* src = "actual selected host declaration" *)
  output host_recovery_clear;
(* src = "actual selected host declaration" *)
  output host_interface_idle;
(* src = "actual selected host declaration" *)
  input obs_dcal_adm_done;
(* src = "actual selected host declaration" *)
  input obs_dcal_cal_ready;
(* src = "actual selected host declaration" *)
  input obs_dcal_running;
(* src = "actual selected host declaration" *)
  input [5:0] obs_dcal_layer;
(* src = "actual selected host declaration" *)
  input [31:0] obs_d2d_recovery_cycles;
  parameter BRIDGE_MUT = 32'b00000000000000000000000000000000;
  parameter D2D_BOOT_ORDER = 32'b00000000000000000000000000000001;
  parameter ENABLE_NATIVE = 32'b00000000000000000000000000000001;
  parameter ENABLE_SERVICE = 32'b00000000000000000000000000000001;
  parameter ENABLE_TOKEN = 32'b00000000000000000000000000000001;
  parameter HC_MUT = 32'b00000000000000000000000000000000;
  parameter MU = 32'b00000000000000000000000000000001;
  parameter NL = 32'b00000000000000000000000000000010;
  parameter ORDER_MUT = 32'b00000000000000000000000000000000;
  parameter PHY_MUT = 32'b00000000000000000000000000000000;
  parameter PROMPT_MUT = 32'b00000000000000000000000000000000;
  parameter QM_MUT = 32'b00000000000000000000000000000000;
  parameter REQUIRE_MISSION_START = 32'b00000000000000000000000000000001;
  parameter T_HBM = 32'b00000000000000110000110101000000;
  parameter T_LINK = 32'b00000000000000110000110101000000;
  parameter WDOG = 32'b00000000010000000000000000000000;
endmodule
