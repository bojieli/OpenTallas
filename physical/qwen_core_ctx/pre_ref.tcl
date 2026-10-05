# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: the stage loaded the plain SDC; apply the die-context boundary.
read_sdc $::env(QCC_SDC_DIR)/io_ref.sdc
puts "QCC boundary referenced to the propagated tree"
