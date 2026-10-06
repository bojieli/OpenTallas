# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: the stage loaded the plain SDC; apply the die-context boundary
# (parasitics first: the reference arrival is measured).
estimate_parasitics -placement
read_sdc $::env(QDM_SDC_DIR)/io_ref_skew.sdc
puts "QDM boundary referenced to the propagated tree"
