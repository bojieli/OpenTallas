foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*_TT_nldm*.lib*] { read_liberty $f }
foreach f [glob -nocomplain /k/macros/*_tt.lib] { read_liberty $f }
read_db /r/4_cts.odb
read_sdc /r/4_cts.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
if {[catch {estimate_parasitics -global_routing} m]} { puts "OT_PAR placement ($m)"; estimate_parasitics -placement } else { puts "OT_PAR global_routing" }
report_worst_slack -max
set a {}; foreach p [get_pins -hierarchical */CLK] { set v [get_property $p arrival_max_rise]; if {$v ne ""} { lappend a $v } }
set a [lsort -real $a]; set n [llength $a]
puts [format "OT_STAT n %d min %.1f p50 %.1f p95 %.1f max %.1f range %.1f" $n [lindex $a 0] [lindex $a [expr {$n/2}]] [lindex $a [expr {int($n*0.95)}]] [lindex $a end] [expr {[lindex $a end]-[lindex $a 0]}]]
