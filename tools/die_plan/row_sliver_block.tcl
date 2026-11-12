# ROW-SLIVER class (KW-FIX-45 11-11, DIE-HBM-100 hbm-qb011-dpl0033): q_b011 failed DPL-0033 because a 6.05 um channel left
# placement-row segments of ~1.9 um between endcaps/tapcells/macros, narrower than the widest wire repeater (BUFx16f) plus
# its two endcaps; 24% of rows had a segment under 3 um.  Opt-in OT_ROW_SLIVER_UM=<W> (default off = this file is never
# sourced, kits byte-identical): after the floorplan/tapcell step every free row segment narrower than W gets a hard
# placement blockage, so no soft cell is placed (and no repeater inserted) in a segment it cannot legalise into.
# Fixed obstacles per row: macros, FIRM/LOCKED cells, endcaps.  Routing is unchanged (placement blockage only).
# rs_slivers rows fixed minw: rows = {{x0 y0 x1 y1} ...} (dbu), fixed = {{x0 y0 x1 y1} ...}; -> {{x0 y0 x1 y1} ...} of the
# free row intervals of width in (0, minw).  Pure Tcl (unit-tested with tclsh).
proc rs_slivers {rows fixed minw} {
  set out {}
  foreach r $rows {
    lassign $r rx0 ry0 rx1 ry1
    set iv {}
    foreach f $fixed {
      lassign $f fx0 fy0 fx1 fy1
      if {$fy0 < $ry1 && $fy1 > $ry0 && $fx0 < $rx1 && $fx1 > $rx0} { lappend iv [list [expr {max($fx0, $rx0)}] [expr {min($fx1, $rx1)}]] }
    }
    set iv [lsort -integer -index 0 $iv]
    set cur $rx0
    foreach s $iv {
      lassign $s a b
      if {$a > $cur && $a - $cur < $minw} { lappend out [list $cur $ry0 $a $ry1] }
      if {$b > $cur} { set cur $b }
    }
    if {$rx1 > $cur && $rx1 - $cur < $minw} { lappend out [list $cur $ry0 $rx1 $ry1] }
  }
  return $out
}
if {[info commands ord::get_db_block] ne "" && [info exists ::env(OT_ROW_SLIVER_UM)] && $::env(OT_ROW_SLIVER_UM) > 0} {
  uplevel #0 {
    set rs_blk [ord::get_db_block]
    set rs_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
    set rs_w [expr {int($::env(OT_ROW_SLIVER_UM) * $rs_dbu)}]
    set rs_rows {}
    foreach r [$rs_blk getRows] { set b [$r getBBox]; lappend rs_rows [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
    set rs_fixed {}
    foreach i [$rs_blk getInsts] {
      set m [$i getMaster]
      if {[$m isBlock] || [$i getPlacementStatus] in {FIRM LOCKED} || [string match "ENDCAP*" [$m getType]]} {
        set b [$i getBBox]; lappend rs_fixed [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
      }
    }
    set rs_n 0
    set rs_log [open $::env(RESULTS_DIR)/ot_row_sliver.txt w]
    foreach r [rs_slivers $rs_rows $rs_fixed $rs_w] {
      lassign $r x0 y0 x1 y1
      odb::dbBlockage_create $rs_blk $x0 $y0 $x1 $y1
      incr rs_n
      puts $rs_log "[expr {$x0 / double($rs_dbu)}]\t[expr {$y0 / double($rs_dbu)}]\t[expr {$x1 / double($rs_dbu)}]\t[expr {$y1 / double($rs_dbu)}]"
    }
    close $rs_log
    puts "OT_ROW_SLIVER: $rs_n free row segments narrower than $::env(OT_ROW_SLIVER_UM) um blocked (of [llength $rs_rows] rows)"
  }
}
