# PATH-S81-PD6 cut evidence: after the combo global_route, dump the GRT per-gcell capacity/usage (dbGCellGrid, written by GRT)
# for every gcell row/col touching each G0 cut line within its partition segment, layers M4-M9; then whole-die sums M4-M7.
source /p/cuts.tcl
set blk [ord::get_db_block]; set tech [[ord::get_db] getTech]; set dbu [$tech getDbUnitsPerMicron]
set g [$blk getGCellGrid]
set GX [$g getGridX]; set GY [$g getGridY]
set nx [llength $GX]; set ny [llength $GY]
puts "OT_GRID nx $nx ny $ny dbu $dbu x0 [lindex $GX 0] x1 [lindex $GX 1] y1 [lindex $GY 1]"
set layers {}
foreach n {M4 M5 M6 M7 M8 M9} { lappend layers [$tech findLayer $n] }
set fh [open /p/gcells_$::env(CORNER).txt w]
proc idx_range {G lo hi} { set n [llength $G]; set r {}; for {set i 0} {$i < $n} {incr i} { set a [lindex $G $i]; if {$i+1<$n} {set b [lindex $G [expr {$i+1}]]} else {set b [expr {$a+1000000}]}; if {$b >= $lo && $a <= $hi} {lappend r $i} }; return $r }
foreach c $CUTS {
  lassign $c o at lo hi
  set A [expr {round($at*$dbu)}]; set LO [expr {round($lo*$dbu)}]; set HI [expr {round($hi*$dbu)}]
  if {$o eq "horizontal"} { set xs [idx_range $GX $LO $HI]; set ys [idx_range $GY [expr {$A-1}] [expr {$A+1}]] } else { set ys [idx_range $GY $LO $HI]; set xs [idx_range $GX [expr {$A-1}] [expr {$A+1}]] }
  foreach xi $xs { foreach yi $ys { foreach l $layers {
    puts $fh "$o $at [$l getName] $xi $yi [lindex $GX $xi] [lindex $GY $yi] [$g getCapacity $l $xi $yi] [$g getUsage $l $xi $yi]"
  } } }
}
close $fh
puts OT_STRIPS_DONE
foreach n {M4 M5 M6 M7} { set l [$tech findLayer $n]; set C 0; set U 0
  for {set xi 0} {$xi < $nx} {incr xi} { for {set yi 0} {$yi < $ny} {incr yi} { incr C [$g getCapacity $l $xi $yi]; incr U [$g getUsage $l $xi $yi] } }
  puts "OT_SUM $n cap $C use $U" }
puts OT_PROBE_DONE
