# HALO-1 follow-up (FABLE-FIX-QC-STA 11-18): POST_TAPCELL.  The hard_cores[].halo_um rings (gen_phys ot_macro_halo, written at
# macro placement) are hard placement blockages; cut_rows then cuts the rows only 2 um from the macro and tapcell puts its
# endcaps / tapcells on those rows, inside a wider ring.  A fixed cell under a hard blockage fails detailed placement:
# QC sle_st_a_v1__cl67389ecd and slw_st_a_v2__clf4365a62 (btab SRAMs, halo_um 4.32) stopped at 3_5 with
# "[WARNING DPL-0004] Placed in rows check failed (1496)" + DPL-0033, every cell a PHY_EDGE / TAP_TAPCELL beside a btab SRAM.
# Here every hard blockage that covers a fixed standard cell is re-cut around those cells (same rule as pg_cell_keepout.tcl:
# no blockage over fixed cells).  The ring still keeps movable cells off the macro edge strip.
# mhc_carve is pure (tested with tclsh, test_macro_halo_carve.py): rect {x0 y0 x1 y1} minus cells -> list of rects.
proc mhc_carve {rect cells} {
  lassign $rect x0 y0 x1 y1
  set hit {}
  foreach c $cells {
    lassign $c a b d e
    if {$d > $x0 && $a < $x1 && $e > $y0 && $b < $y1} { lappend hit [list [expr {max($a, $x0)}] [expr {max($b, $y0)}] [expr {min($d, $x1)}] [expr {min($e, $y1)}]] }
  }
  if {![llength $hit]} { return [list $rect] }
  set ys [list $y0 $y1]
  foreach h $hit { lappend ys [lindex $h 1] [lindex $h 3] }
  set ys [lsort -integer -unique $ys]
  set out {}; set prev {}; set py0 ""
  for {set i 0} {$i < [llength $ys] - 1} {incr i} {
    set ya [lindex $ys $i]; set yb [lindex $ys [expr {$i + 1}]]
    set iv {}
    foreach h $hit { lassign $h a b d e; if {$e > $ya && $b < $yb} { lappend iv [list $a $d] } }
    set segs {}; set x $x0
    foreach v [lsort -integer -index 0 $iv] { lassign $v a d; if {$a > $x} { lappend segs [list $x $a] }; if {$d > $x} { set x $d } }
    if {$x < $x1} { lappend segs [list $x $x1] }
    if {$py0 ne "" && $segs eq $prev} continue
    if {$py0 ne ""} { foreach s $prev { lappend out [list [lindex $s 0] $py0 [lindex $s 1] $ya] } }
    set prev $segs; set py0 $ya
  }
  foreach s $prev { lappend out [list [lindex $s 0] $py0 [lindex $s 1] $y1] }
  return $out
}
proc mhc_run {} {
  set blk [ord::get_db_block]
  set fixed {}
  foreach i [$blk getInsts] {
    if {[[$i getMaster] isBlock] || [$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
    set b [$i getBBox]; lappend fixed [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  set nb 0; set np 0; set nc 0
  foreach b [$blk getBlockages] {
    if {[$b isSoft] || [$b getInstance] ne "NULL"} continue
    set q [$b getBBox]; set x0 [$q xMin]; set y0 [$q yMin]; set x1 [$q xMax]; set y1 [$q yMax]
    set near {}
    foreach c $fixed { lassign $c a e d f; if {$d > $x0 && $a < $x1 && $f > $y0 && $e < $y1} { lappend near $c } }
    if {![llength $near]} continue
    set parts [mhc_carve [list $x0 $y0 $x1 $y1] $near]
    odb::dbBlockage_destroy $b
    foreach p $parts { odb::dbBlockage_create $blk {*}$p; incr np }
    incr nb; incr nc [llength $near]
  }
  puts "OT_MACRO_HALO_CARVE $nb hard blockage(s) re-cut into $np around $nc fixed cell(s) (tapcells / endcaps stay legal for DPL)"
}
if {[llength [info commands ord::get_db_block]]} { mhc_run }
