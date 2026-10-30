# Same standard PG-only keepout cleanup, now at the actual H13 channel boundaries.
source /work/keepout_phys.tcl
set b [ord::get_db_block];set dbu [[ord::get_db_tech] getDbUnitsPerMicron];set rects {}
foreach i [$b getInsts] {
 if {![[$i getMaster] isBlock]} {continue}
 set r [$i getBBox];set core [$b getCoreArea]
 foreach side {W E} {
  if {$side eq "W"} {set x0 [expr {max([$core xMin],[$r xMin]-round(12.96*$dbu))}];set x1 [$r xMin]} else {set x0 [$r xMax];set x1 [expr {min([$core xMax],[$r xMax]+round(12.96*$dbu))}]}
  set y0 [expr {max([$core yMin],[$r yMin]-round(6.3*$dbu))}];set y1 [expr {min([$core yMax],[$r yMax]+round(6.3*$dbu))}]
  lappend rects [list $x0 $y0 $x1 $y1]
 }
}
ot_clear_keepout_physical $b $rects btab_h13_pincolumns
