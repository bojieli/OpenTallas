# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {stream_clk stream_bank_clk[0] stream_bank_clk[1] hbm_clk hbm_fifo_clk[0] hbm_fifo_clk[1] hbm_pc_clk[0] hbm_pc_clk[1] hbm_pc_clk[2] hbm_pc_clk[3]}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hdie_svg_fg2w/clock_entry.sdc
}
