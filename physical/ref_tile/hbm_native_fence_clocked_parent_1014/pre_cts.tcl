# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl); cluster: balanced clock spine with child-insertion leaf targets (sourced FIRST, so the io_ref wrapper below wraps it)
source /src/physical/common_flow/clock_spine.tcl
source /src/physical/ref_tile/hbm_native_fence_clocked_parent_1014/spine_ins.tcl
source /src/physical/hbm_native_fence_clocked_1014/own_root_cts.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/hbm_native_fence_clocked_1014/physical_boundary.tcl
}
