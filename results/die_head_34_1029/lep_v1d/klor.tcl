read_db /out/after.odb
set b [ord::get_db_block]
set u [$b getDbUnitsPerMicron]
set bt [$b findBTerm k_lo_r]
set net [$bt getNet]
set moved {}
for {set k 0} {$k < 12} {incr k} {
  set drv ""
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { set drv $it } }
  if {$drv eq ""} { puts "OT_KLOR no driver"; break }
  set inst [$drv getInst]; set m [[$inst getMaster] getName]
  set loc [$inst getLocation]
  puts "OT_KLOR hop $k [$inst getName] $m [expr {[lindex $loc 0]/double($u)}] [expr {[lindex $loc 1]/double($u)}]"
  lappend moved $inst
  if {![regexp {^(BUF|INV|HB)} $m]} { break }
  set in ""
  foreach it [$inst getITerms] { if {[$it isInputSignal]} { set in $it } }
  set net [$in getNet]
}
set x 4.0; set y 4.32
foreach inst $moved {
  $inst setLocation [expr {round($x*$u)}] [expr {round($y*$u)}]
  $inst setPlacementStatus PLACED
  set x [expr {$x + 1.5}]
}
detailed_placement
check_placement -verbose
foreach inst $moved { set loc [$inst getLocation]; puts "OT_KLOR_NEW [$inst getName] [expr {[lindex $loc 0]/double($u)}] [expr {[lindex $loc 1]/double($u)}]" }
write_db /out/after_klor.odb
puts OT_DONE
