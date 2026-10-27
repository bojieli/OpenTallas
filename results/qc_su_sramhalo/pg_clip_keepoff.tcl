# Local QC prog trial: keep the full planned pin strip except actual PG metal/via footprints + margin.
proc pc_sub {r h} {
 lassign $r x y X Y;lassign $h a b A B
 if {$X<=$a || $x>=$A || $Y<=$b || $y>=$B} {return [list $r]}
 set a [expr {max($x,$a)}];set A [expr {min($X,$A)}];set b [expr {max($y,$b)}];set B [expr {min($Y,$B)}]
 set out {};foreach q [list [list $x $y $a $Y] [list $A $y $X $Y] [list $a $y $A $b] [list $a $B $A $Y]] {lassign $q x0 y0 x1 y1;if {$x1>$x0 && $y1>$y0} {lappend out $q}}
 return $out
}
set b [ord::get_db_block];set u [$b getDbUnitsPerMicron];set tech [ord::get_db_tech]
set X [expr {round(7.074*$u)}];set Y [expr {round(2.16*$u)}];set I [expr {round(.30*$u)}];set margin [expr {round(.128*$u)}]
set pg {}
foreach n [$b getNets] {
 if {[$n getSigType] ni {POWER GROUND}} continue
 foreach sw [$n getSWires] {foreach w [$sw getWires] {
  if {![$w isVia]} {lappend pg [list [[$w getTechLayer] getName] [$w xMin] [$w yMin] [$w xMax] [$w yMax]];continue}
  lassign [$w getViaXY] vx vy
  set v [$w getTechVia];if {$v eq "NULL"} {set v [$w getBlockVia]}
  if {$v eq "NULL"} {error "PC_CLIP missing PG via definition"}
  foreach q [$v getBoxes] {set l [$q getTechLayer];if {$l eq "NULL"} continue;lappend pg [list [$l getName] [expr {$vx+[$q xMin]}] [expr {$vy+[$q yMin]}] [expr {$vx+[$q xMax]}] [expr {$vy+[$q yMax]}]]}
 }}
}
set fp [open $::env(RESULTS_DIR)/pincol_pg_clip.txt w];set nbox 0;set pieces_count 0
foreach inst [$b getInsts] {
 if {![[$inst getMaster] isBlock]} continue
 set bb [$inst getBBox];set X0 [$bb xMin];set X1 [$bb xMax];set Y0 [$bb yMin];set Y1 [$bb yMax]
 set faces {}
 foreach it [$inst getITerms] {
  if {[$it getNet] eq "NULL" || [[$it getNet] getSigType] in {POWER GROUND}} continue
  set r [$it getBBox]
  if {[$r xMin]-$X0<$u/10} {lappend faces W} elseif {$X1-[$r xMax]<$u/10} {lappend faces E}
 }
 foreach side [lsort -unique $faces] {foreach end {S N} {
  set ya [expr {$end eq "N" ? $Y1-$I : $Y0-$Y}];set yb [expr {$end eq "N" ? $Y1+$Y : $Y0+$I}]
  set outer [expr {$side eq "E" ? [list $X1 [expr {$X1+$X}]] : [list [expr {$X0-$X}] $X0]}]
  set inner [expr {$side eq "E" ? [list [expr {$X1-$X}] $X1] : [list $X0 [expr {$X0+$X}]]}]
  foreach lay {M2 M3 M4 M5} {foreach part {outer inner} {
   if {$part eq "inner" && $lay ne "M5"} continue
   lassign [set $part] xa xb;set pieces [list [list $xa $ya $xb $yb]];incr nbox
   foreach pr $pg {
    lassign $pr pl px py pX pY
    if {$pl ne $lay || $pX+$margin<=$xa || $px-$margin>=$xb || $pY+$margin<=$ya || $py-$margin>=$yb} continue
    set next {};foreach q $pieces {lappend next {*}[pc_sub $q [list [expr {$px-$margin}] [expr {$py-$margin}] [expr {$pX+$margin}] [expr {$pY+$margin}]]]};set pieces $next
   }
   foreach q $pieces {
    odb::dbObstruction_create $b [$tech findLayer $lay] {*}$q;incr pieces_count
    puts $fp "PC_CLIP [$inst getName] $side$end $lay $part $q"
   }
  }}
 }}
}
close $fp
puts "PC_CLIP original_boxes $nbox pieces $pieces_count pg_shapes [llength $pg] margin_um .128; PG wires/vias retained"
