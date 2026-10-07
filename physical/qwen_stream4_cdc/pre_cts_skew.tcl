# PRE_CTS_TCL (margin): build the tree on the plain SDC, then switch to the die-context boundary (io_skew.sdc,
# OT_IO_SKEW / OT_IO_HOLD_SKEW) before the CTS-stage repair, re-applied after every parasitics estimate.
proc qcd_apply_io {} { read_sdc $::env(QCD_SDC_DIR)/io_skew.sdc }
rename clock_tree_synthesis ::qcd_cts_orig
proc clock_tree_synthesis {args} {
  ::qcd_cts_orig {*}$args
  rename estimate_parasitics ::qcd_est_orig
  proc ::estimate_parasitics {args} { ::qcd_est_orig {*}$args; qcd_apply_io }
  estimate_parasitics -placement
}
