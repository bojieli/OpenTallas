# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); clock entries: no tree, one port per child clock pin (sourced FIRST)
set ::ot_ce_cts_roots {clk clk_n clk_s clk_e clk_w}
source /src/physical/common_flow/clock_entries.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/ref_tile/vm_native_q0_faces_g313/clock_entry.sdc
}
