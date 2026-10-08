# PRE_CTS_TCL: build the tree on the plain SDC, then switch to the die-context boundary before CTS-stage repair.
source $::env(QCC_SDC_DIR)/repair_budget.tcl
rename clock_tree_synthesis ::qcc_cts_orig
proc clock_tree_synthesis {args} {
  ::qcc_cts_orig {*}$args
  read_sdc $::env(QCC_SDC_DIR)/io_ref_skew.sdc
  puts "QCC boundary referenced to the propagated tree"
}
