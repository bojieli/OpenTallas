foreach name [list $::env(PG_READ_CASE)] {
 read_db /work/$name.odb
 set b [ord::get_db_block];set rows {};set ports {}
 foreach n [$b getNets] {
  if {[$n getSigType] in {POWER GROUND}} continue
  set wire {};set w [$n getWire]
  if {$w ne "NULL"} {for {set j 0} {$j<[$w length]} {incr j} {lappend wire [list [$w getOpcode $j] [$w getData $j]]}}
  set guides {};foreach g [$n getGuides] {set r [$g getBox];lappend guides [list [[$g getLayer] getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]}
  lappend rows [list [$n getName] $wire [lsort $guides]]
 }
 foreach t [$b getBTerms] {
  set pins {};foreach p [$t getBPins] {set boxes {};foreach box [$p getBoxes] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]};lappend pins [list [$p getPlacementStatus] [lsort $boxes]]}
  lappend ports [list [$t getName] [$t getSigType] [$t getIoType] [lsort $pins]]
 }
 set f [open /work/${name}_routing_guard.tcl {WRONLY CREAT EXCL}];puts $f [list [lsort $rows] [lsort $ports]];close $f
}
puts NATIVE_POST_REPAIR_ROUTING_BTERM_GUARDS_EXTRACTED
