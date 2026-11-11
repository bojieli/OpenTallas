# DS85-HEHOT macro-move what-if (GRT only, DO_NOT_COUNT, in-memory only). hca swap identical to grt_hca.tcl, then
# MOVES="inst:x_um:y_um[:orient];..." sets each instance's placement bbox lower-left (std cells are not legalised:
# GRT sees moved macro pins/OBS; cells left under a moved macro keep their pins). IT congestion iterations.
read_db /r/4_cts.odb
set db [ord::get_db]; set b [ord::get_db_block]; set u [$b getDbUnitsPerMicron]
set fh [open /l/swap.list]; set pairs {}
while {[gets $fh line] >= 0} { if {[string trim $line] eq ""} continue; lassign $line old lef; read_lef -library /l/$lef; lappend pairs $old }
close $fh
set n 0
foreach i [$b getInsts] { set nm [[$i getMaster] getName]; if {[lsearch -exact $pairs $nm] < 0} continue
  if {![$i swapMaster [$db findMaster ${nm}_hca]]} { error "swap failed" }; incr n }
puts "WI $::env(WI) swapped $n"
foreach mv [split $::env(MOVES) ";"] {
  if {[string trim $mv] eq ""} continue
  set f [split $mv ":"]; set inst [$b findInst [lindex $f 0]]
  if {$inst eq "NULL"} { error "no inst [lindex $f 0]" }
  if {[llength $f] > 3} { $inst setOrient [lindex $f 3] }
  $inst setPlacementStatus PLACED
  set bb [$inst getBBox]; set lx [lindex [$inst getLocation] 0]; set ly [lindex [$inst getLocation] 1]
  set dx [expr {round([lindex $f 1]*$u) - [$bb xMin]}]; set dy [expr {round([lindex $f 2]*$u) - [$bb yMin]}]
  $inst setLocation [expr {$lx+$dx}] [expr {$ly+$dy}]; $inst setPlacementStatus FIRM
  set bb [$inst getBBox]
  puts "WI_MOVE [$inst getName] [$inst getOrient] [expr {[$bb xMin]/double($u)}] [expr {[$bb yMin]/double($u)}] [expr {[$bb xMax]/double($u)}] [expr {[$bb yMax]/double($u)}]"
}
set_routing_layers -signal M2-M7 -clock M2-M7
foreach {l a} {M2 0.5 M3 0.5 M4 0.25 M5 0.25 M6 0.30 M7 0.30} { set_global_routing_layer_adjustment $l $a }
foreach i [$b getInsts] { set m [$i getMaster]; if {[$m isBlock]} { set bb [$i getBBox]; puts "WI_MACRO [$i getName] [$m getName] [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]" } }
set t0 [clock seconds]
global_route -congestion_iterations $::env(IT) -allow_congestion -verbose -congestion_report_file /o/$::env(WI).congestion.rpt
puts "WI_DONE [expr {[clock seconds]-$t0}] s"
