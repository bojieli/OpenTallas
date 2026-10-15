# ref_tile PRE_CTS: io_ref boundary switch after the tree (qwen_die_masters/pre_cts_skew.tcl)
source /src/physical/ref_tile/s81hc_ctfxnt_ref/clock_split.tcl
source /src/physical/qwen_die_masters/pre_cts_skew.tcl
rename clock_tree_synthesis ::ot_ref_cts_boundary_orig
proc clock_tree_synthesis {args} {
  ::ot_ref_cts_boundary_orig {*}$args
  set ::ot_ref_pre_cts 0
  source /src/physical/common_flow/hold_pad_hb4.tcl
  source /src/physical/ref_tile/s81hc_ctfxnt_ref/local_clock_tap.tcl
  source /src/physical/ref_tile/s81hc_ctfxnt_ref/capture_driver_size.tcl
}
