# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: the stage loaded the plain SDC; apply the S1 die-context boundary.
read_sdc $::env(QSS_SDC_DIR)/io_ref.sdc
puts "QSS S1 boundary referenced to the propagated tree"
