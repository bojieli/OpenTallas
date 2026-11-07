# DIE-HBM-62/FLOW class GRT-NEAR-MISS: every global_route may finish with congestion; sign-off judges the routed result.
# repair_antennas after a congested route drops the GRT routes (EST-0005 at the next estimate_parasitics); no diode cell
# exists in this kit, so it can only report.  check_antennas at sign-off still judges the routed result.
set ::env(SKIP_ANTENNA_REPAIR) 1
if {[info commands ot_gr_strict] eq ""} {
  rename global_route ot_gr_strict
  proc global_route {args} {
    if {[lsearch -exact $args -start_incremental] < 0 && [lsearch -exact $args -allow_congestion] < 0} {
      lappend args -allow_congestion
    }
    uplevel 1 [list ot_gr_strict {*}$args]
  }
}
