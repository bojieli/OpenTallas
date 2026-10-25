# IO-HOLD A/B probe: the kit's post-CTS FF hold gate (hold_gate.tcl, this dir; io_hold.tcl beside it = option A)
# then a census of every FF hold-violating endpoint by class (startpoint port = IN->REG, endpoint port = REG->OUT).
if {[catch {source [file join [file dirname [file normalize [info script]]] hold_gate.tcl]} e]} { puts "GATE_ERROR $e" }
set pes [find_timing_paths -path_delay min -slack_max 0 -group_path_count 1000000 -endpoint_path_count 1]
array set cz_n {}; array set cz_w {}; array set cz_s {}; array set cz_bus {}
foreach pe $pes {
  set sp [get_full_name [get_property $pe startpoint]]
  set ep [get_full_name [get_property $pe endpoint]]
  set sl [get_property $pe slack]
  if {[llength [get_ports -quiet $sp]]} { set c IN_REG; set b [regsub {\[[0-9]+\]$} $sp {}]; if {![info exists cz_bus($b)]} {set cz_bus($b) 0}; incr cz_bus($b)
  } elseif {[llength [get_ports -quiet $ep]]} { set c REG_OUT } else { set c R2R }
  if {![info exists cz_n($c)]} { set cz_n($c) 0; set cz_w($c) 0.0; set cz_s($c) 0.0 }
  incr cz_n($c); set cz_s($c) [expr {$cz_s($c) + $sl}]; if {$sl < $cz_w($c)} { set cz_w($c) $sl }
}
foreach c {IN_REG R2R REG_OUT} {
  if {[info exists cz_n($c)]} { puts [format "CENSUS %s n %d worst %.2f tns %.1f" $c $cz_n($c) $cz_w($c) $cz_s($c)] } else { puts "CENSUS $c n 0 worst 0 tns 0" }
}
foreach b [lsort [array names cz_bus]] { puts "CENSUS_BUS $b $cz_bus($b)" }
puts "CENSUS_TOTAL [llength $pes]"
