# Source-defined interior input-collar capture sites, after face_flops.tcl
uplevel #0 {

proc ci_overlap {a b} {
  lassign $a ax ay az aw; lassign $b bx by bz bw
  return [expr {$ax < $bz && $bx < $az && $ay < $bw && $by < $aw}]
}
proc ci_put_near {f px py} {
  global ff_blk ff_dbu ff_rows ff_cpitch ff_x0 ff_x1 ff_orient
  set w [[$f getMaster] getWidth]; set h [[$f getMaster] getHeight]
  set keep {}
  foreach b [$ff_blk getBlockages] {
    set q [$b getBBox]; lappend keep [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]
  }
  foreach i [$ff_blk getInsts] {
    if {$i eq $f || ![$i isFixed]} continue
    set q [$i getBBox]; lappend keep [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]
  }
  set col [expr {round(double($px-$ff_x0)/$ff_cpitch)}]; set candidates {}
  foreach row $ff_rows {
    lassign [$row getOrigin] rx y
    if {abs($y-$py) > 30*$ff_dbu} continue
    for {set dx -14} {$dx <= 14} {incr dx} {
      set x [expr {$ff_x0+($col+$dx)*$ff_cpitch}]
      set d [expr {abs($x-$px)+abs($y-$py)}]
      if {$x < $ff_x0 || $x+$w > $ff_x1 || $d > 30*$ff_dbu} continue
      lappend candidates [list $d $x $y]
    }
  }
  foreach p [lsort -integer -index 0 $candidates] {
    lassign $p d x y; set r [list $x $y [expr {$x+$w}] [expr {$y+$h}]]; set bad 0
    foreach q $keep {if {[ci_overlap $r $q]} {set bad 1; break}}
    if {$bad} continue
    $f setPlacementStatus PLACED
    if {[dict exists $ff_orient $y]} {$f setOrient [dict get $ff_orient $y]}
    $f setLocation $x $y; $f setPlacementStatus FIRM
    return [list $x $y]
  }
  error "PC_INPUT_COLLAR: no legal interior capture within30um"
}

set ci_bt [$ff_blk findBTerm {rst_n[0]}]
if {$ci_bt eq "NULL"} { error "PC_INPUT_COLLAR: missing interior input pin" }
set ci_f [ff_from_in [$ci_bt getNet] 0]
if {$ci_f eq ""} { error "PC_INPUT_COLLAR: missing interior capture" }
set ci_x [expr {round(199.128*$ff_dbu)}]
set ci_y [expr {round(181.44*$ff_dbu)}]
lassign [ci_put_near $ci_f $ci_x $ci_y] ci_ax ci_ay
if {abs($ci_ax-$ci_x)+abs($ci_ay-$ci_y) > 30*$ff_dbu} { error "PC_INPUT_COLLAR: interior capture exceeds30um" }
puts "PC_INPUT_COLLAR interior [$ci_bt getName] -> [$ci_f getName] at $ci_ax $ci_ay"
}
