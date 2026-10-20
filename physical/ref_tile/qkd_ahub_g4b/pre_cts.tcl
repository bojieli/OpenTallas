# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_c ck_w ck_e ck_z0 ck_z1 ck_z2 ck_z3}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_nhb_zh} 4 {ot_qkh_recip_leaf} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/qkd_ahub_g4b/clock_entry.sdc
}
