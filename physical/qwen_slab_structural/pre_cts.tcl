# PRE_CTS_TCL: build the tree on the plain (ideal-referenced) SDC, then switch to the S1 die-context boundary before
# the CTS-stage repair_timing (hold repair) runs.  Tested: Codex twoface_570 placement, physical/README S1 evidence.
rename clock_tree_synthesis ::qss_cts_orig
proc clock_tree_synthesis {args} {
  ::qss_cts_orig {*}$args
  read_sdc $::env(QSS_SDC_DIR)/io_ref.sdc
  puts "QSS S1 boundary referenced to the propagated tree"
}
