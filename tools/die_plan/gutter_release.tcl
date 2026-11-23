# GENERATED copy of tools/die_plan/gutter_release.tcl (sourced by face_flops_release.tcl, PRE_DETAIL_PLACE).
# S81-TYPES-5 11-07 NARROW-GUTTER: gutter_block.tcl's placement blockages steer global placement only; they are removed
# before DPL, because tap cells and FIRM landing cells inside a gutter fail check_placement ("placed in rows",
# COLH10 vS DPL-0033 on 40592 cells).  Only the blockages listed in ot_gutter_block.txt are removed.
# GUTTER-KEEP 11-23: OT_GUTTER_BLOCK_KEEP=1 (budgets.gutter_block_keep_types) keeps the blockages instead (see below).
# gr_carve = mhc_carve of macro_halo_carve.tcl (pure: rect minus cells -> rects).
proc gr_carve {rect cells} {
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
uplevel #0 {
set gr_f $::env(RESULTS_DIR)/ot_gutter_block.txt
if {[file exists $gr_f]} {
  set gr_blk [ord::get_db_block]
  set gr_u [[ord::get_db_tech] getDbUnitsPerMicron]
  set gr_want {}
  set fh [open $gr_f r]
  foreach ln [split [read $fh] "\n"] {
    if {$ln eq ""} continue
    lassign [split $ln "\t"] a b c d
    dict set gr_want "[expr {round($a * $gr_u)}],[expr {round($b * $gr_u)}],[expr {round($c * $gr_u)}],[expr {round($d * $gr_u)}]" 1
  }
  close $fh
  set gr_n 0
  set gr_kept {}
  set gr_keep [expr {[info exists ::env(OT_GUTTER_BLOCK_KEEP)] && $::env(OT_GUTTER_BLOCK_KEEP) eq "1"}]
  foreach k [$gr_blk getBlockages] {
    set bb [$k getBBox]
    if {[dict exists $gr_want "[$bb xMin],[$bb yMin],[$bb xMax],[$bb yMax]"]} {
      if {$gr_keep} { lappend gr_kept [list [$bb xMin] [$bb yMin] [$bb xMax] [$bb yMax]] }
      odb::dbBlockage_destroy $k; incr gr_n
    }
  }
  if {$gr_keep} {
    # GUTTER-KEEP 11-23 (FABLE-OPEN-KV, KV rc118 pc slits): the blockage stays for DPL, the resizer, CTS and GRT repair; it is
    # re-cut around every fixed standard cell (tapcells, endcaps, FIRM landing cells), so "placed in rows" holds for them.
    set gr_fixed {}
    foreach i [$gr_blk getInsts] {
      if {[[$i getMaster] isBlock] || [$i getPlacementStatus] ni {FIRM LOCKED COVER}} continue
      set b [$i getBBox]; lappend gr_fixed [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
    }
    set gr_np 0; set gr_nc 0
    foreach q $gr_kept {
      lassign $q x0 y0 x1 y1
      set near {}
      foreach c $gr_fixed { lassign $c a e d f; if {$d > $x0 && $a < $x1 && $f > $y0 && $e < $y1} { lappend near $c } }
      foreach p [gr_carve $q $near] { odb::dbBlockage_create $gr_blk {*}$p; incr gr_np }
      incr gr_nc [llength $near]
    }
    puts "OT_GUTTER_BLOCK kept [llength $gr_kept] of [dict size $gr_want] gutter placement blockages through DPL (re-cut into $gr_np around $gr_nc fixed cells)"
  } else {
  puts "OT_GUTTER_BLOCK removed $gr_n of [dict size $gr_want] gutter placement blockages before DPL"
  }
}
}
