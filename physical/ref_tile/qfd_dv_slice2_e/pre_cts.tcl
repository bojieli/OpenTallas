# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_core ck_hd ck_ef ck_wf ck_nw ck_nc ck_ne ck_sw ck_sc ck_se}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {qfd_dv_lane_h} 8 {ot_hdc_sfu_rcp_t} 8 {ot_hdc_sfu_exp_t} 8 {ot_hdc_sfu_rsq_t} 8 {ot_qfd_xs_leaf} 32]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qfd_dv_slice2_e/clock_entry.sdc
}
