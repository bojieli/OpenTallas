# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_t ck_upn ck_upne ck_c ck_cpw ck_cw ck_ce ck_cpe ck_u ck_xs ck_mpse}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hbm_sm_pv_merge_s3} 1 {ot_hbm_accel_smh_tct} 1 {ot_hbm_accel_smh_bdc} 1 {ot_hbm_accel_smh_tcl_gu} 2 {ot_hbm_accel_smh_xs} 1 {ot_smh_tr_group_row_w} 1 {ot_smh_tr_group_row_e} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/smh_rp7s_f/clock_entry.sdc
}
