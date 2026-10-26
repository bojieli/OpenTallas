# Move ONLY generated well taps out of the newly reserved E5 clock islands.
# No functional cells, masters, orientations, nets, or clock edges change.
proc ot_e5_tap_relocations {mode {out /work/clock_tap_relocations.tsv}} {
 set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set boxes {}
 foreach y {258.12 353.16} {foreach x {237.06 312.12} {lappend boxes [list [expr {round($x*$u)}] [expr {round($y*$u)}] [expr {round(($x+5.94)*$u)}] [expr {round(($y+4.32)*$u)}]]}}
 proc ot_e5_overlap {a b} {lassign $a x0 y0 x1 y1;lassign $b a0 b0 a1 b1;expr {$x0<$a1 && $x1>$a0 && $y0<$b1 && $y1>$b0}}
 proc ot_e5_bbox {i} {set r [$i getBBox];list [$r xMin] [$r yMin] [$r xMax] [$r yMax]}
 set bad {};set ys {};set by {}
 foreach i [$b getInsts] {
  if {![string match TAP_TAPCELL_ROW_* [$i getName]]} continue
  set bb [ot_e5_bbox $i];set hit 0;foreach box $boxes {if {[ot_e5_overlap $bb $box]} {set hit 1;break}}
  if {!$hit} continue
  foreach it [$i getITerms] {if {[$it getSigType] ni {POWER GROUND}} {error "E5 TAP-only guard found a functional pin"}}
  lassign [$i getLocation] x y;lappend ys $y;lappend bad [list $i $x $y]
 }
 set ys [lsort -unique -integer $ys]
 set rows {};foreach r [$b getRows] {lassign [$r getOrigin] x y;if {$y in $ys} {dict lappend rows $y [list $x [$r getSpacing] [$r getSiteCount] [$r getOrient]]}}
 set badnames {};foreach z $bad {dict set badnames [[lindex $z 0] getName] 1}
 set busy {};foreach i [$b getInsts] {
  if {[$i getPlacementStatus] ni {FIRM LOCKED COVER} || [dict exists $badnames [$i getName]]} continue
  set bb [ot_e5_bbox $i];lassign $bb x0 y0 x1 y1
  foreach y $ys {if {$y<$y1 && $y+270>$y0} {dict lappend busy $y $bb}}
 }
 set plan {}
 foreach z $bad {
  lassign $z i x y;set m [$i getMaster];set w [$m getWidth];set h [$m getHeight];set orient [$i getOrient];set target {}
  for {set ring 1} {$ring<=160 && ![llength $target]} {incr ring} {
   foreach sign {-1 1} {
    set nx [expr {$x+$sign*$ring*54}];set bb [list $nx $y [expr {$nx+$w}] [expr {$y+$h}]];set okay 0
    foreach row [dict get $rows $y] {lassign $row rx pitch count ro;if {$ro eq $orient && $nx>=$rx && ($nx-$rx)%$pitch==0 && $nx+$w<=$rx+$pitch*$count} {set okay 1;break}}
    if {!$okay} continue
    foreach box $boxes {if {[ot_e5_overlap $bb $box]} {set okay 0;break}}
    if {$okay && [dict exists $busy $y]} {foreach box [dict get $busy $y] {if {[ot_e5_overlap $bb $box]} {set okay 0;break}}}
    if {$okay} {set target [list $nx $y];dict lappend busy $y $bb;break}
   }
  }
  if {![llength $target]} {error "E5 no adjacent same-row well-tap site outside clock island for [$i getName]"}
  lappend plan [list $i $x $y {*}$target]
 }
 set f [open $out w];puts $f "name\told_x_um\told_y_um\tnew_x_um\tnew_y_um"
 foreach z $plan {lassign $z i x y nx ny;puts $f "[$i getName]\t[expr {$x/double($u)}]\t[expr {$y/double($u)}]\t[expr {$nx/double($u)}]\t[expr {$ny/double($u)}]"}
 close $f
 if {$mode eq "apply"} {
  foreach z $plan {lassign $z i x y nx ny;set ps [$i getPlacementStatus];set o [$i getOrient];$i setPlacementStatus PLACED;$i setLocation $nx $ny;$i setOrient $o;$i setPlacementStatus $ps;if {[lrange [ot_e5_bbox $i] 0 1] ne [list $nx $ny]} {error "E5 TAP actual moved bbox mismatch"}}
 } elseif {$mode ne "plan"} {error "E5 bad TAP phase"}
 puts "E5_CLOCK_TAP $mode [llength $plan] physical-only welltaps at <=8.64um same-row offsets; all functional cells unchanged"
}
