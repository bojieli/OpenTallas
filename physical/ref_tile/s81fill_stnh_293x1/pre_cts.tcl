# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl) + forwarded-clock subtree kept (hbm_w2_rb_station forwarded_subtree.tcl)
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/s81_station_native/fwd_clock_out.tcl
}
source /src/physical/hbm_w2_rb_station_20261006/forwarded_subtree.tcl
