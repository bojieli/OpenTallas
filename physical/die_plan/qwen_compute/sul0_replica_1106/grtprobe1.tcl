read_db $::env(ODB)
set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
set keep 0
foreach n [$b getNets] {
  if {[$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"} continue
  set lo 0; set hi 0; set east 1
  foreach it [$n getITerms] { set r [$it getAvgXY]; if {[lindex $r 0]} { set x [expr {[lindex $r 1]/double($u)}]; set y [expr {[lindex $r 2]/double($u)}]; if {$x < 250} {set east 0}; if {$y <= 726.3} {set lo 1}; if {$y >= 993.1} {set hi 1} } }
  if {$lo && $hi && $east && $keep < 1 && [llength [$n getBTerms]] == 0} { incr keep; puts "PROBE1 keep [$n getName]"; continue }
  foreach it [$n getITerms] { $it disconnect }; foreach bt [$n getBTerms] { odb::dbBTerm_destroy $bt }
}
if {[info exists ::env(NOPDN)]} {
  foreach n [$b getNets] { if {[$n getSigType] eq "POWER" || [$n getSigType] eq "GROUND"} { foreach w [$n getSWires] { odb::dbSWire_destroy $w } } }
  puts "PROBE1 PDN special wires removed"
}
set_routing_layers -signal M2-M7 -clock M2-M7
global_route -allow_congestion -verbose -congestion_iterations 0 -congestion_report_file /out/probe1_$::env(TAG).rpt
