# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {clk clk_lg[0] clk_lg[1] clk_lg[2] clk_lg[3] clk_map[0] clk_map[1] clk_map[2] clk_map[3] clk_map[4] clk_map[5] clk_map[6] clk_map[7] clk_map[8] clk_map[9] clk_map[10] clk_map[11] clk_map[12] clk_map[13] clk_map[14] clk_map[15]}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_sfucore_split/clock_entry.sdc
}
