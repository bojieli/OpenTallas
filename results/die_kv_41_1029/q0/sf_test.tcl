foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_TT_nldm*.lib*] { read_liberty $f }
foreach f [glob -nocomplain /k/macros/*_tt.lib] { read_liberty $f }
read_db /r/4_cts.odb
read_sdc /r/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
proc stats {tag} {
  set a {}; foreach p [get_pins -hierarchical */CLK] { set v [get_property $p arrival_max_rise]; if {$v ne ""} { lappend a $v } }
  set a [lsort -real $a]; set n [llength $a]
  puts [format "OT_STAT %s n %d min %.1f p50 %.1f p95 %.1f max %.1f" $tag $n [lindex $a 0] [lindex $a [expr {$n/2}]] [lindex $a [expr {int($n*0.95)}]] [lindex $a end]]
}
report_worst_slack -max
stats before
source /o/strip_feed.tcl
stats after
report_worst_slack -max
report_worst_slack -min
puts OT_DONE
