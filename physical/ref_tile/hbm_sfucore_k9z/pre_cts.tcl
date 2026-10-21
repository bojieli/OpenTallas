# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {clk clk_pw clk_pe clk_st[0] clk_st[1] clk_st[2] clk_st[3] clk_st[4] clk_lg[0] clk_lg[1] clk_lg[2] clk_lg[3] clk_map_0 clk_map_1 clk_map_2 clk_map_3 clk_map_4 clk_map_5 clk_map_6 clk_map_7 clk_map_8 clk_map_9 clk_map_10 clk_map_11 clk_map_12 clk_map_13 clk_map_14 clk_map_15}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hbm_sfucore_k9z/clock_entry.sdc
}
