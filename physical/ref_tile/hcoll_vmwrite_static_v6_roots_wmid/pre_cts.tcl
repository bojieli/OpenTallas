# ref_tile PRE_CTS: independent related leaf CTS roots; measure each domain boundary after CTS
set ::ot_ce_cts_roots {clk_body clk_meta clk_rgx_ctrl clk_tkw clk_rgx_data0 clk_rgx_data1 clk_rgx_data2 clk_rgx_data3 clk_bank0 clk_bank1 clk_bank2 clk_bank3 clk_bank4 clk_bank5 clk_bank6 clk_bank7}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/repair_budget.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  estimate_parasitics -placement
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hcoll_vmwrite_static_v6_roots_wmid/clock_entry.sdc
}
