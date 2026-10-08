# m3 copy: reads io_refpin_skew_m3.sdc
# PRE_CTS_TCL: build the tree on the plain (ideal-referenced) SDC, then switch to the S1 die-context boundary
# (io_refpin_skew_m3.sdc) before the CTS-stage repair_timing runs, re-applied after every parasitics estimate.
proc qss_apply_io {} {
  read_sdc $::env(QSS_SDC_DIR)/io_refpin_skew_m3.sdc
  puts "QSS S1 boundary referenced to the propagated tree"
}
source $::env(QSS_SDC_DIR)/rom_lead.tcl
rename clock_tree_synthesis ::qss_cts_orig
proc clock_tree_synthesis {args} {
  ::qss_cts_orig {*}$args
  qss_rom_lead [expr {[info exists ::env(QSS_ROM_LEAD_BUFS)] ? $::env(QSS_ROM_LEAD_BUFS) : 0}]
  rename estimate_parasitics ::qss_est_orig
  proc ::estimate_parasitics {args} {
    ::qss_est_orig {*}$args
    qss_apply_io
  }
  estimate_parasitics -placement
}
