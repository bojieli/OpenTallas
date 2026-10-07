# PRE_CTS_TCL: build the tree on the plain SDC, then switch to the die-context boundary before CTS-stage repair.
source $::env(QDM_SDC_DIR)/repair_budget.tcl
rename clock_tree_synthesis ::qdm_cts_orig
proc clock_tree_synthesis {args} {
  ::qdm_cts_orig {*}$args
  estimate_parasitics -placement
  read_sdc $::env(QDM_SDC_DIR)/io_ref_skew.sdc
  puts "QDM boundary referenced to the propagated tree"
}
