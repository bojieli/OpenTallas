# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {ck leaf_ck[0] leaf_ck[1] leaf_ck[2] leaf_ck[3] leaf_ck[4] leaf_ck[5] leaf_ck[6] leaf_ck[7] leaf_ck[8]}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/s81bf_col_ten_roots_w_h03/clock_entry.sdc
}
