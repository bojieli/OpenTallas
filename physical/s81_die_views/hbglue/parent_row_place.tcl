# Deterministic standard-cell row placement for the compact native glue.
# Replaces only numerical GPL; DPL, repair, CTS, routing and STA remain real.
proc ot_head_row_place {args} {
 set block [ord::get_db_block]
 set dbu [$block getDbUnitsPerMicron]
 if {$dbu!=1000} {error "native site coordinates require 1000 DBU/um"}
 set rows {}
 foreach row [$block getRows] {
  lassign [$row getOrigin] ox y
  set site [$row getSite]; set sw [$site getWidth]; set sh [$site getHeight]
  if {$y < 48600 || $y+$sh > 89640} {continue}
  set left [expr {max($ox,125280)}]
  set left [expr {$ox+int(ceil(double($left-$ox)/$sw))*$sw}]
  set right [expr {min($ox+[$row getSiteCount]*$sw,174960)}]
  if {$right-$left <1000} {continue}
  lappend rows [list $y $left $right $row $sw $sh]
 }
 set rows [lsort -integer -index 0 $rows]
 if {[llength $rows]<100} {error "missing central legal row coverage"}
 set blocked [dict create]
 set cells {}
 foreach inst [$block getInsts] {
  if {[$inst isFixed]} {
   set bb [$inst getBBox]
   foreach r $rows {
    lassign $r y left right row sw sh
    if {[$bb yMin]<$y+$sh && [$bb yMax]>$y} {dict lappend blocked $row [list [$bb xMin] [$bb xMax]]}
   }
  } else {lappend cells [list [$inst getName] $inst]}
 }
 set cells [lsort -dictionary -index 0 $cells]
 set next [dict create]
 foreach r $rows {lassign $r y left right row sw sh;dict set next $row $left}
 set k 0;set count 0
 foreach pair $cells {
  lassign $pair name inst
  set w [[$inst getMaster] getWidth];set h [[$inst getMaster] getHeight]
  set placed 0
  for {set trial 0} {$trial<[llength $rows]} {incr trial} {
   set ri [expr {($k+$trial)%[llength $rows]}]
   lassign [lindex $rows $ri] y left right row sw sh
   if {$h>$sh} {continue}
   set x [dict get $next $row]
   set changed 1
   while {$changed} {
    set changed 0
    if {[dict exists $blocked $row]} {
     foreach iv [dict get $blocked $row] {
      lassign $iv a b
      if {$x<$b && $x+$w>$a} {set x [expr {$left+int(ceil(double($b-$left)/$sw))*$sw}];set changed 1}
     }
    }
   }
   if {$x+$w>$right} {continue}
   $inst setOrient [$row getOrient]
   $inst setLocation $x $y
   $inst setPlacementStatus PLACED
   # Reserve empty sites for signal and later repair cells at ~60% row fill.
   dict set next $row [expr {$x+int(ceil(double($w)/$sw/0.60))*$sw}]
   set k [expr {($ri+1)%[llength $rows]}]
   set placed 1;incr count;break
  }
  if {!$placed} {error "native compact rows exhausted at $name"}
 }
 puts "OT_HEAD_NATIVE_ROW_PLACE cells=$count legal_rows=[llength $rows] box=125.28,48.60,174.96,89.64"
 if {[all_pins_placed]} {check_placement -verbose}
}
rename global_placement ot_head_unused_numerical_gpl
proc global_placement {args} {ot_head_row_place {*}$args}
