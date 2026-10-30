read_db $::env(ODB)
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
set da [$b getDieArea]
puts $f "DIE [expr {[$da xMax]/double($u)}] [expr {[$da yMax]/double($u)}]"
foreach i [$b getInsts] {
  set bb [$i getBBox]
  puts $f "[$i getName] [[$i getMaster] getName] [expr {[$bb xMin]/double($u)}] [expr {[$bb yMin]/double($u)}] [expr {[$bb xMax]/double($u)}] [expr {[$bb yMax]/double($u)}] [$i getPlacementStatus]"
}
close $f
