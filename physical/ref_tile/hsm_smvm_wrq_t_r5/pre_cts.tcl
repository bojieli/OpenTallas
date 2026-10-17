# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {clk clk_l0 clk_l1 clk_l2 clk_l3 clk_l4 clk_l5 clk_l6 clk_l7}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/hsm_smvm_wrq_t_r5/clock_entry.sdc
}
