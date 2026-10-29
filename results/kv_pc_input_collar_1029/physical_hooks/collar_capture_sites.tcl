# One diagnostic PLACE source constraint. No RTL/cycle or clock change.
uplevel #0 {
source /work/collar_capture_data.tcl
set cc_b [ord::get_db_block];set cc_u [$cc_b getDbUnitsPerMicron]
set cc_rows {};set cc_orient {}
foreach row [$cc_b getRows] {
 lassign [$row getOrigin] x y;set bb [$row getBBox]
 dict lappend cc_rows $y [list [$bb xMin] [$bb xMax]]
 dict set cc_orient $y [$row getOrient]
}
set cc_match {};set cc_ids {}
foreach p $cc_plans {
 lassign $p raw norm master x y w h;set found {}
 foreach n [list $raw $norm] {set i [$cc_b findInst $n];if {$i ne "NULL" && [lsearch -exact $found $i]<0} {lappend found $i}}
 if {[llength $found]!=1} {error "PC_COLLAR_CAPTURE: missing/ambiguous $raw"}
 set i [lindex $found 0]
 if {[[$i getMaster] getName] ne $master} {error "PC_COLLAR_CAPTURE: actual master drift $raw"}
 if {[[$i getMaster] getWidth]>round($w*$cc_u) || [[$i getMaster] getHeight]>round($h*$cc_u)} {error "PC_COLLAR_CAPTURE: body exceeds planned bound $raw"}
 dict set cc_ids [$i getId] 1;lappend cc_match [list $i $p]
}
proc cc_ov {a b} {lassign $a x y z w;lassign $b X Y Z W;return [expr {$x<$Z && $X<$z && $y<$W && $Y<$w}]}
set cc_keep {}
foreach k [$cc_b getBlockages] {set q [$k getBBox];lappend cc_keep [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]}
foreach i [$cc_b getInsts] {
 if {[dict exists $cc_ids [$i getId]] || ![$i isFixed]} continue
 set q [$i getBBox];lappend cc_keep [list [$q xMin] [$q yMin] [$q xMax] [$q yMax]]
}
set cc_steps {}
for {set dy -3} {$dy<=3} {incr dy} {for {set dx -18} {$dx<=18} {incr dx} {
 set x [expr {round($dx*.054*$cc_u)}];set y [expr {round($dy*.27*$cc_u)}];set dist [expr {abs($x)+abs($y)}]
 if {$dist<=$cc_u} {lappend cc_steps [list $dist $x $y]}
}}
set cc_steps [lsort -integer -index 0 $cc_steps];set cc_homes {}
foreach item $cc_match {
 lassign $item i p;lassign $p raw norm master ax ay aw ah
 set mx [expr {round($ax*$cc_u)}];set my [expr {round($ay*$cc_u)}]
 set w [[$i getMaster] getWidth];set h [[$i getMaster] getHeight];set home {}
 foreach s $cc_steps {
  lassign $s dd dx dy;set x [expr {$mx+$dx}];set y [expr {$my+$dy}]
  if {![dict exists $cc_rows $y]} continue
  set inrow 0;foreach rr [dict get $cc_rows $y] {lassign $rr a z;if {$a<=$x && $x+$w<=$z} {set inrow 1;break}}
  if {!$inrow} continue
  set rect [list $x $y [expr {$x+$w}] [expr {$y+$h}]];set bad 0
  foreach k $cc_keep {if {[cc_ov $rect $k]} {set bad 1;break}}
  if {$bad} continue
  set home [list $i $x $y $rect $dd];break
 }
 if {![llength $home]} {error "PC_COLLAR_CAPTURE: no row/fixed/island-clear body within1um of $raw"}
 lappend cc_homes $home;lappend cc_keep [lindex $home 3]
}
set out [open $::env(RESULTS_DIR)/collar_capture_homes.tsv w]
foreach home $cc_homes {
 lassign $home i x y rect dd
 $i setPlacementStatus PLACED;$i setOrient [dict get $cc_orient $y];$i setLocation $x $y;$i setPlacementStatus FIRM
 puts $out "[$i getName]\t[[$i getMaster] getName]\t$x\t$y\t$dd"
}
close $out
puts "PC_COLLAR_CAPTURE PASS names/master/bounds/rows/fixed/islands [llength $cc_homes] exact actual homes"
}
