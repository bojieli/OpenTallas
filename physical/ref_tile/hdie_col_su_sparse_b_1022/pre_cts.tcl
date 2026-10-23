# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {clk_in clk}
set ::env(OT_SPINE_PORTS) {clk_in,clk}
set ::env(OT_SPINE_CTS_REST) 0
source /src/physical/common_flow/clock_spine.tcl
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hdie_col_su_sparse_b_1022/clock_entry.sdc
}
