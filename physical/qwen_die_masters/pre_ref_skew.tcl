# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: the stage loaded the plain SDC; apply the die-context boundary
source $::env(QDM_SDC_DIR)/repair_budget.tcl
# (parasitics first: the reference arrival is measured).
estimate_parasitics -placement
read_sdc $::env(QDM_SDC_DIR)/io_ref_skew.sdc
# el1013-smh-r14: opt-in per-clock-class reference of the ports of a second clock class (io_ref_class.sdc)
if {[info exists ::env(OT_IO_REF_CLASS)] && $::env(OT_IO_REF_CLASS) eq "1"} { read_sdc $::env(QDM_SDC_DIR)/io_ref_class.sdc }
puts "QDM boundary referenced to the propagated tree"
