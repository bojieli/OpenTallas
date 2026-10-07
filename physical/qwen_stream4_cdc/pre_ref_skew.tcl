# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL (margin): re-apply the die-context boundary after every parasitics estimate
source $::env(PLATFORM_DIR)/setRC.tcl
proc qcd_apply_io {} { read_sdc $::env(QCD_SDC_DIR)/io_skew.sdc }
if {[llength [info commands ::qcd_est_orig]] == 0} {
  rename estimate_parasitics ::qcd_est_orig
  proc estimate_parasitics {args} { ::qcd_est_orig {*}$args; qcd_apply_io }
}
estimate_parasitics -placement
