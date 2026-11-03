# Generated physical reservation for accepted die clock driver islands.
uplevel #0 {
set di_b [ord::get_db_block]
set di_u [[ord::get_db_tech] getDbUnitsPerMicron]
source /work/keepout_phys.tcl
set di_rects {}
set di_count 0; set di_area 0.0; set di_rows 0
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(284.58*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(285.39*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(284.85*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(285.66*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(474.66*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(475.47*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(1044.9*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(1045.71*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(1045.17*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(1045.98*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(1234.98*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(1235.79*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(1235.25*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(1236.06*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.018*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(38.718*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.828*$di_u)}]; set di_y0 [expr {round(92.34*$di_u)}]
set di_x1 [expr {round(38.286*$di_u)}]; set di_y1 [expr {round(93.15*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.828*$di_u)}]; set di_y0 [expr {round(187.11*$di_u)}]
set di_x1 [expr {round(38.286*$di_u)}]; set di_y1 [expr {round(187.92*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(36.828*$di_u)}]; set di_y0 [expr {round(949.86*$di_u)}]
set di_x1 [expr {round(38.286*$di_u)}]; set di_y1 [expr {round(950.67*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(284.58*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(285.39*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(284.85*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(285.66*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(474.66*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(475.47*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(1044.9*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(1045.71*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(1045.17*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(1045.98*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(1234.98*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(1235.79*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(1235.25*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(1236.06*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(37.638*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(40.338*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(38.07*$di_u)}]; set di_y0 [expr {round(92.34*$di_u)}]
set di_x1 [expr {round(39.528*$di_u)}]; set di_y1 [expr {round(93.15*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(38.07*$di_u)}]; set di_y0 [expr {round(187.11*$di_u)}]
set di_x1 [expr {round(39.528*$di_u)}]; set di_y1 [expr {round(187.92*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(38.07*$di_u)}]; set di_y0 [expr {round(949.86*$di_u)}]
set di_x1 [expr {round(39.528*$di_u)}]; set di_y1 [expr {round(950.67*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(170.964*$di_u)}]; set di_y0 [expr {round(646.92*$di_u)}]
set di_x1 [expr {round(172.422*$di_u)}]; set di_y1 [expr {round(647.73*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(170.964*$di_u)}]; set di_y0 [expr {round(1407.24*$di_u)}]
set di_x1 [expr {round(172.422*$di_u)}]; set di_y1 [expr {round(1408.05*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(172.206*$di_u)}]; set di_y0 [expr {round(646.92*$di_u)}]
set di_x1 [expr {round(173.664*$di_u)}]; set di_y1 [expr {round(647.73*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(172.206*$di_u)}]; set di_y0 [expr {round(1407.24*$di_u)}]
set di_x1 [expr {round(173.664*$di_u)}]; set di_y1 [expr {round(1408.05*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(196.668*$di_u)}]; set di_y0 [expr {round(563.22*$di_u)}]
set di_x1 [expr {round(199.368*$di_u)}]; set di_y1 [expr {round(564.03*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(196.668*$di_u)}]; set di_y0 [expr {round(563.49*$di_u)}]
set di_x1 [expr {round(199.368*$di_u)}]; set di_y1 [expr {round(564.3*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(196.668*$di_u)}]; set di_y0 [expr {round(956.61*$di_u)}]
set di_x1 [expr {round(199.368*$di_u)}]; set di_y1 [expr {round(957.42*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(313.308*$di_u)}]; set di_y0 [expr {round(759.78*$di_u)}]
set di_x1 [expr {round(316.008*$di_u)}]; set di_y1 [expr {round(760.59*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(355.698*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(358.398*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(355.698*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(358.398*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(355.698*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(358.398*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(355.698*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(358.398*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(355.698*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(358.398*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(355.698*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(358.398*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(356.508*$di_u)}]; set di_y0 [expr {round(92.34*$di_u)}]
set di_x1 [expr {round(357.966*$di_u)}]; set di_y1 [expr {round(93.15*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.318*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(360.018*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.318*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(360.018*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.318*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(360.018*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.318*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(360.018*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.318*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(360.018*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.318*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(360.018*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(357.75*$di_u)}]; set di_y0 [expr {round(92.34*$di_u)}]
set di_x1 [expr {round(359.208*$di_u)}]; set di_y1 [expr {round(93.15*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(189.54*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(190.35*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(189.81*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(190.62*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(379.62*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(380.43*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(379.89*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(380.7*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(569.7*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(570.51*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(569.97*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(570.78*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(949.86*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(950.67*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(950.13*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(950.94*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(1139.94*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(1140.75*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(1140.21*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(1141.02*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.348*$di_u)}]; set di_y0 [expr {round(1330.02*$di_u)}]
set di_x1 [expr {round(519.048*$di_u)}]; set di_y1 [expr {round(1330.83*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.564*$di_u)}]; set di_y0 [expr {round(266.76*$di_u)}]
set di_x1 [expr {round(518.022*$di_u)}]; set di_y1 [expr {round(267.57*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.564*$di_u)}]; set di_y0 [expr {round(646.92*$di_u)}]
set di_x1 [expr {round(518.022*$di_u)}]; set di_y1 [expr {round(647.73*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.564*$di_u)}]; set di_y0 [expr {round(1027.08*$di_u)}]
set di_x1 [expr {round(518.022*$di_u)}]; set di_y1 [expr {round(1027.89*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(516.564*$di_u)}]; set di_y0 [expr {round(1407.24*$di_u)}]
set di_x1 [expr {round(518.022*$di_u)}]; set di_y1 [expr {round(1408.05*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(517.806*$di_u)}]; set di_y0 [expr {round(266.76*$di_u)}]
set di_x1 [expr {round(519.264*$di_u)}]; set di_y1 [expr {round(267.57*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(517.806*$di_u)}]; set di_y0 [expr {round(646.92*$di_u)}]
set di_x1 [expr {round(519.264*$di_u)}]; set di_y1 [expr {round(647.73*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(517.806*$di_u)}]; set di_y0 [expr {round(1027.08*$di_u)}]
set di_x1 [expr {round(519.264*$di_u)}]; set di_y1 [expr {round(1027.89*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(517.806*$di_u)}]; set di_y0 [expr {round(1407.24*$di_u)}]
set di_x1 [expr {round(519.264*$di_u)}]; set di_y1 [expr {round(1408.05*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(574.668*$di_u)}]; set di_y0 [expr {round(759.78*$di_u)}]
set di_x1 [expr {round(577.368*$di_u)}]; set di_y1 [expr {round(760.59*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(675.378*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(678.078*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(675.378*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(678.078*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(675.378*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(678.078*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(675.378*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(678.078*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(675.378*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(678.078*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(675.378*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(678.078*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(676.998*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(679.698*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(676.998*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(679.698*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(676.998*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(679.698*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(676.998*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(679.698*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(676.998*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(679.698*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(676.998*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(679.698*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(836.028*$di_u)}]; set di_y0 [expr {round(900.18*$di_u)}]
set di_x1 [expr {round(838.728*$di_u)}]; set di_y1 [expr {round(900.99*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(836.028*$di_u)}]; set di_y0 [expr {round(1322.46*$di_u)}]
set di_x1 [expr {round(838.728*$di_u)}]; set di_y1 [expr {round(1323.27*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(836.028*$di_u)}]; set di_y0 [expr {round(1322.73*$di_u)}]
set di_x1 [expr {round(838.728*$di_u)}]; set di_y1 [expr {round(1323.54*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(836.028*$di_u)}]; set di_y0 [expr {round(1520.1*$di_u)}]
set di_x1 [expr {round(838.728*$di_u)}]; set di_y1 [expr {round(1520.64*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(863.136*$di_u)}]; set di_y0 [expr {round(646.92*$di_u)}]
set di_x1 [expr {round(864.594*$di_u)}]; set di_y1 [expr {round(647.73*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(863.136*$di_u)}]; set di_y0 [expr {round(1407.24*$di_u)}]
set di_x1 [expr {round(864.594*$di_u)}]; set di_y1 [expr {round(1408.05*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(864.378*$di_u)}]; set di_y0 [expr {round(646.92*$di_u)}]
set di_x1 [expr {round(865.836*$di_u)}]; set di_y1 [expr {round(647.73*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(864.378*$di_u)}]; set di_y0 [expr {round(1407.24*$di_u)}]
set di_x1 [expr {round(865.836*$di_u)}]; set di_y1 [expr {round(1408.05*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(284.58*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(285.39*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(284.85*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(285.66*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(474.66*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(475.47*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(1044.9*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(1045.71*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(1045.17*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(1045.98*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(1234.98*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(1235.79*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(1235.25*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(1236.06*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.058*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(997.758*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.868*$di_u)}]; set di_y0 [expr {round(92.34*$di_u)}]
set di_x1 [expr {round(997.596*$di_u)}]; set di_y1 [expr {round(93.15*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.868*$di_u)}]; set di_y0 [expr {round(187.11*$di_u)}]
set di_x1 [expr {round(997.326*$di_u)}]; set di_y1 [expr {round(187.92*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(995.868*$di_u)}]; set di_y0 [expr {round(949.86*$di_u)}]
set di_x1 [expr {round(997.326*$di_u)}]; set di_y1 [expr {round(950.67*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(94.5*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(95.31*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(94.77*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(95.58*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(284.58*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(285.39*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(284.85*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(285.66*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(474.66*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(475.47*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(664.74*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(665.55*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(854.82*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(855.63*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(855.09*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(855.9*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(1044.9*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(1045.71*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(1045.17*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(1045.98*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(1234.98*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(1235.79*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(1235.25*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(1236.06*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.678*$di_u)}]; set di_y0 [expr {round(1425.06*$di_u)}]
set di_x1 [expr {round(999.378*$di_u)}]; set di_y1 [expr {round(1425.87*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(996.84*$di_u)}]; set di_y0 [expr {round(92.34*$di_u)}]
set di_x1 [expr {round(998.568*$di_u)}]; set di_y1 [expr {round(93.15*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(997.11*$di_u)}]; set di_y0 [expr {round(187.11*$di_u)}]
set di_x1 [expr {round(998.568*$di_u)}]; set di_y1 [expr {round(187.92*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
set di_x0 [expr {round(997.11*$di_u)}]; set di_y0 [expr {round(949.86*$di_u)}]
set di_x1 [expr {round(998.568*$di_u)}]; set di_y1 [expr {round(950.67*$di_u)}]
odb::dbBlockage_create $di_b $di_x0 $di_y0 $di_x1 $di_y1
lappend di_rects [list $di_x0 $di_y0 $di_x1 $di_y1]
incr di_count
set di_area [expr {$di_area + ($di_x1-$di_x0)*($di_y1-$di_y0)/double($di_u*$di_u)}]
foreach di_r [$di_b getRows] {
  set di_box [$di_r getBBox]
  if {[$di_box xMin]<$di_x1 && [$di_box xMax]>$di_x0 && [$di_box yMin]<$di_y1 && [$di_box yMax]>$di_y0} { incr di_rows }
}
ot_clear_keepout_physical $di_b $di_rects die_clock_islands
puts "OT_DIE_ISLANDS blockages=$di_count rectangle_area_sum_um2=$di_area row_intersections=$di_rows"
}
