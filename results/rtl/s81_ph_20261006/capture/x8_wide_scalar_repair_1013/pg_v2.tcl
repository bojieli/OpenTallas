read_db /base/6_final.odb
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
set total 0
set face 0
foreach net [$block getNets] {
 if {![$net isSpecial]} continue
 foreach sw [$net getSWires] {
  foreach box [$sw getWires] {
   set layer [$box getTechLayer]
   if {$layer eq "NULL" || [$layer getName] ne "M5"} continue
   incr total
   set x0 [expr {[$box xMin]/double($dbu)}]; set x1 [expr {[$box xMax]/double($dbu)}]
   set y0 [expr {[$box yMin]/double($dbu)}]; set y1 [expr {[$box yMax]/double($dbu)}]
   puts "PG_M5 [$net getName] $x0 $y0 $x1 $y1"
   if {($y0 <= 0.192 && $y1 >= 0) || ($y0 <= 136.08 && $y1 >= 135.888)} {incr face}
  }
 }
}
puts "PG_M5_SUMMARY total=$total face_intersections=$face"
exit
