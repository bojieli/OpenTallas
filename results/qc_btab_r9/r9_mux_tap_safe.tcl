# Existing 512 deterministic mux placements: repair only a collision with a fixed physical cell, within same grid.
set mb [ord::get_db_block];set mu [$mb getDbUnitsPerMicron]
set mf [open /work/r9_mux_bounds.txt];set bounds [read $mf];close $mf
proc cm_index {b} {
 set ::cm_occ {}
 foreach j [$b getInsts] {
  if {[$j getPlacementStatus] ni {FIRM LOCKED COVER}} continue
  set r [$j getBBox];set rec [list [$j getName] [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
  for {set k [expr {[$r yMin]/270}]} {$k<=[expr {([$r yMax]-1)/270}]} {incr k} {dict lappend ::cm_occ $k $rec}
 }
}
proc cm_free {b skip x y w h} {
 for {set k [expr {$y/270}]} {$k<=[expr {($y+$h-1)/270}]} {incr k} {
  if {![dict exists $::cm_occ $k]} continue
  foreach rec [dict get $::cm_occ $k] {
   lassign $rec n a c A C
   if {$n ne $skip && $x+$w+108>$a && $x-108<$A && $y+$h>$c && $y<$C} {return 0}
  }
 }
 return 1
}
cm_index $mb
set changed 0
foreach line [split $bounds \n] {
 if {$line eq ""} continue
 lassign $line n x0 y0 x1 y1
 set i [$mb findInst $n];set r [$i getBBox];set x [$r xMin];set y [$r yMin];set w [[$i getMaster] getWidth];set h [[$i getMaster] getHeight]
 if {[cm_free $mb $n $x $y $w $h]} continue
 set best {};set cost 1e30
 set xa [expr {4320+int(ceil(($x0*$mu-4320)/54.0))*54}];set xb [expr {round($x1*$mu)}];set ya [expr {4320+int(ceil(($y0*$mu-4320)/270.0))*270}];set yb [expr {round($y1*$mu)}]
 for {set Y $ya} {$Y+$h<=$yb} {incr Y 270} {
  for {set X $xa} {$X+$w<=$xb} {incr X 54} {
   set c [expr {abs($X-$x)+abs($Y-$y)}]
   if {$c>=$cost || ![cm_free $mb $n $X $Y $w $h]} continue
   set cost $c;set best [list $X $Y]
  }
 }
 if {$best eq ""} {error "R9_MUX no TAP-clear site within original grid $n"}
 lassign $best X Y
 set orient "";foreach row [$mb getRows] {if {[lindex [$row getOrigin] 1]==$Y} {set orient [$row getOrient];break}}
 if {$orient eq ""} {error "R9_MUX missing row $Y"}
 $i setPlacementStatus PLACED
 $i setOrient $orient;$i setLocation $X $Y
 $i setPlacementStatus FIRM
 puts "R9_MUX_TAP_MOVE $n [expr {$x/double($mu)}] [expr {$y/double($mu)}] -> [expr {$X/double($mu)}] [expr {$Y/double($mu)}]"
 incr changed
 cm_index $mb
}
puts "R9_MUX_TAP_SAFE moved $changed; fixed mux footprints use actual TAP obstacles"
