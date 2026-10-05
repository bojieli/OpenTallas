# PRE_CTS_TCL: build the tree on the plain (ideal-referenced) SDC, then switch to the S1 die-context boundary
# (io_wc.sdc) before the CTS-stage repair_timing runs, re-applied after every parasitics estimate.
proc qss_apply_io {} {
  read_sdc $::env(QSS_SDC_DIR)/io_wc.sdc
  puts "QSS S1 boundary referenced to the propagated tree"
}
rename clock_tree_synthesis ::qss_cts_orig
proc clock_tree_synthesis {args} {
  ::qss_cts_orig {*}$args
  rename estimate_parasitics ::qss_est_orig
  proc ::estimate_parasitics {args} {
    ::qss_est_orig {*}$args
    qss_apply_io
  }
  estimate_parasitics -placement
}
