# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck_ctl ck_q0 ck_q1 ck_q2 ck_q3}
set ::ot_ce_landed_cluster 1
set ::ot_ce_counts [dict create {ot_hidx_s3_q} 4 {ot_hidx_s3_ctl} 1]
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hidx_sel_s3p_c24s/clock_entry.sdc
}
