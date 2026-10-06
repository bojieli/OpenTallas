# m3 copy of post_plain.tcl (kept separate so the m3 hooks are one set)
# POST_{CTS,GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: restore the plain boundary so the written stage SDC can be
# loaded by the next stage (a -reference_pin SDC crashes load_design).
read_sdc $::env(QSS_SDC_DIR)/io_plain.sdc
