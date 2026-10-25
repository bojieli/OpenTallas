# HBM-CORES3 10-25 (COORD CORRECTION 00:46): post-CTS FF hold gate. STOP (structural -> plan/RTL fix, no repair)
# when FF hold WNS < -100 ps or > 2000 hold endpoints on the CTS tree (placement RC, SDC 25 ps hold uncertainty).
foreach l [split $::env(PLIBS)] { if {$l ne ""} { read_liberty $l } }
read_db $::env(ODB)
read_sdc $::env(SDC)
set_propagated_clock [get_clocks clk]
source $::env(PLATFORM_DIR)/setRC.tcl
estimate_parasitics -placement
set n 0; set wns 0.0
foreach p [find_timing_paths -path_delay min -group_path_count 2001 -endpoint_path_count 1 -slack_max 0] {
  incr n
  set s [get_property $p slack]
  if {$s < $wns} { set wns $s }
}
set verdict PASS
if {$wns < -100.0 || $n > 2000} { set verdict FAIL }
puts "OT_HOLD_GATE $verdict wns_ps [format %.2f $wns] endpoints $n (limits wns -100 ps, 2000 endpoints; counted up to 2001 per group)"
