# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_n ck_s}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hbm_accel_smh_xs} 8 {ot_hbm_accel_smh_bdc} 8 {ot_hbm_accel_smh_tct} 8 {ot_hbm_accel_smh_tcl} 16 {ot_smh_tr_group_beat_e} 2 {ot_smh_tr_group_row_w} 2 {ot_smh_tr_group_land} 2 {ot_smh_tr_group_row_e} 2]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hnx_rp4lp4/clock_entry.sdc
}
