# S81/KITS post-CTS FF hold gate (COORD 00:46): STOP if FF hold WNS < -100 ps or > 2000 violating hold endpoints.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 4_cts.odb 4_cts.sdc
estimate_parasitics -placement
set wns [sta::worst_slack_cmd min]
if {[catch {set n [sta::endpoint_violation_count min]}]} {
  set n [llength [find_timing_paths -path_delay min -group_path_count 100000 -endpoint_path_count 1 -slack_max 0]]
}
set f [open $::env(GATE_OUT) w]
puts $f "CTS_HOLD_FF wns_ps [format %.2f [expr {$wns * 1e12}]] violators $n"
close $f
puts "CTS_HOLD_FF wns_ps [format %.2f [expr {$wns * 1e12}]] violators $n"
