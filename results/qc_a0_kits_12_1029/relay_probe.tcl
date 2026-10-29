read_db /odb/2_floorplan.odb
set b [ord::get_db_block]; set u [[ord::get_db_tech] getDbUnitsPerMicron]
foreach {nm x0 y0 x1 y1} {relay 135.0 873.0 139.0 877.0 root 311.0 668.0 315.0 672.0} {
 set n 0
 foreach i [$b getInsts] { set bb [$i getBBox]
  if {[$bb xMax] > $x0*$u && [$bb xMin] < $x1*$u && [$bb yMax] > $y0*$u && [$bb yMin] < $y1*$u} { puts "$nm OVL [$i getName] w=[expr ([$bb xMax]-[$bb xMin])/$u.] [[$i getMaster] getName] [$i getPlacementStatus] [expr [$bb xMin]/$u.] [expr [$bb yMin]/$u.]"; incr n } }
 set r 0
 foreach row [$b getRows] { set rb [$row getBBox]; if {[$rb yMin] <= $y0*$u+2000 && [$rb yMax] >= $y0*$u+2000 && [$rb xMin] <= $x0*$u && [$rb xMax] >= $x1*$u} {incr r; puts "$nm ROW [$row getName] y [expr [$rb yMin]/$u.] x [expr [$rb xMin]/$u.]-[expr [$rb xMax]/$u.]"} }
 puts "$nm overlaps=$n rows=$r"
}
