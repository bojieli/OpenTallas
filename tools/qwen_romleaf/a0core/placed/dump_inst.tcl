# usage: openroad -no_init -exit with env ODB, OUT: name master isBlock x0 y0 x1 y1 (um) per instance
read_db $::env(ODB)
set b [ord::get_db_block]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set f [open $::env(OUT) w]
foreach i [$b getInsts] {
  set bb [$i getBBox]
  puts $f [format "%s\t%s\t%d\t%.3f\t%.3f\t%.3f\t%.3f" [$i getName] [[$i getMaster] getName] [[$i getMaster] isBlock] \
    [expr {[$bb xMin]/double($dbu)}] [expr {[$bb yMin]/double($dbu)}] [expr {[$bb xMax]/double($dbu)}] [expr {[$bb yMax]/double($dbu)}]]
}
close $f
set g [open $::env(OUT).regions w]
foreach r [$b getRegions] { foreach bx [$r getBoundaries] { puts $g [format "%s\t%s\t%.3f\t%.3f\t%.3f\t%.3f" [$r getName] [$r getRegionType] [expr {[$bx xMin]/double($dbu)}] [expr {[$bx yMin]/double($dbu)}] [expr {[$bx xMax]/double($dbu)}] [expr {[$bx yMax]/double($dbu)}]] } }
close $g
