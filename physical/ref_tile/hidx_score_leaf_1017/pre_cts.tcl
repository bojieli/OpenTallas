# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {clk clk_pair[0] clk_pair[1] clk_pair[2] clk_pair[3] clk_pair[4] clk_pair[5] clk_pair[6] clk_pair[7] clk_pair[8] clk_pair[9] clk_pair[10] clk_pair[11] clk_pair[12] clk_pair[13] clk_pair[14] clk_pair[15]}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hidx_score_leaf_1017/clock_entry.sdc
}
