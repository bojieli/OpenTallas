# m3 copy: reads io_refpin_skew_m3.sdc
# PRE_{GLOBAL_ROUTE,DETAIL_ROUTE,FILLCELL}_TCL: the stage loaded the plain SDC; apply the S1 die-context boundary
# (io_refpin_skew_m3.sdc: the reference register's propagated WC arrival), and re-apply it after every parasitics estimate so
# the boundary tracks the current tree and parasitics.
source $::env(PLATFORM_DIR)/setRC.tcl
proc qss_apply_io {} {
  read_sdc $::env(QSS_SDC_DIR)/io_refpin_skew_m3.sdc
  puts "QSS S1 boundary referenced to the propagated tree"
}
if {[llength [info commands ::qss_est_orig]] == 0} {
  rename estimate_parasitics ::qss_est_orig
  proc estimate_parasitics {args} {
    ::qss_est_orig {*}$args
    qss_apply_io
  }
}
estimate_parasitics -placement
