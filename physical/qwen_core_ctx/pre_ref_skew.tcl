# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: the stage loaded the plain SDC; apply the die-context boundary.
source $::env(QCC_SDC_DIR)/repair_budget.tcl
# The boundary reference is the propagated clock arrival at a register of this tree, so parasitics must be present
# when io_ref_skew.sdc measures it (without them the GRT stage measured ~207 ps instead of ~310 ps).
estimate_parasitics -placement
read_sdc $::env(QCC_SDC_DIR)/io_ref_skew.sdc
puts "QCC boundary referenced to the propagated tree"
