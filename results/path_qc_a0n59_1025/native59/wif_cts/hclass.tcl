# PATH-QC-A0N59 read-only FF hold census by endpoint class (same setup as hold_gate.tcl up to the check)
foreach l $::env(PLIBS) { read_liberty $l }
read_db $::env(ODB); read_sdc $::env(SDC); set_propagated_clock [all_clocks]
source /work/vclk_corner.tcl; ot_vclk_bind ff
source $::env(LAYER_PARASITICS_FILE); estimate_parasitics -placement
set paths [find_timing_paths -path_delay min -group_path_count 5000 -endpoint_path_count 1 -slack_max 0]
array set n {}; array set w {}
foreach p $paths {
  set e [get_full_name [get_property $p endpoint]]; set s [get_full_name [get_property $p startpoint]]
  set sl [get_property $p slack]
  if {[string match *u_mem/* $e]} {regexp {/([a-z_]+)} [string range $e [string last / $e] end] -> pin; set c "MACRO_[expr {[string match *g_wif* $s] ? {WIF} : {other}}]_$pin"} \
  elseif {[string match *u_mem/* $s]} {set c "FROM_MACRO"} \
  elseif {[llength [get_ports -quiet $s]]} {set c IN_PORT} else {set c R2R}
  if {![info exists n($c)]} {set n($c) 0; set w($c) 0}
  incr n($c); if {$sl < $w($c)} {set w($c) $sl}
}
foreach c [lsort [array names n]] {puts [format "HCLASS %-28s n=%5d wns=%8.2f" $c $n($c) [expr {$w($c)*1e12}]]}
set p [lindex $paths 0]; puts "WORST [get_full_name [get_property $p startpoint]] -> [get_full_name [get_property $p endpoint]]"
