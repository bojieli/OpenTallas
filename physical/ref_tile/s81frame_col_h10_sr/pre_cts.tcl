# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_r0 ck_r1 ck_r2}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {dsfd_qbank_N} 12 {dsfd_qbank_S} 12 {dsfd_cfifo_crs4} 1 {ot_v41_rom_elem_q_qxpq_w10} 12 {dsfd_bf_front_roots} 4 {ot_v41_bf_col} 8 {dsfd_node_LLfu} 8 {dsfd_node_NNfu} 7 {dsfd_node_LLfd} 7 {dsfd_node_NNfd} 8 {dsfd_node_LLd} 1 {dsfd_rstg} 3 {ot_s81_cfg7_seq} 12 {ot_s81_cfg7_seq_bfp} 4 {ot_s81_sstn_base566} 10 {ot_s81_sstn_payload536} 10 {dsfd_dvrly_276_NS} 4]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81frame_col_h10_sr/clock_entry.sdc
}
