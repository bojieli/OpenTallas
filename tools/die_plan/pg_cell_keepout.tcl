# pg_cell_keepout.tcl (PG-AWARE-1 2026-11-14, FABLE-WAVE-REVIEW fix 6 S2(b)): no standard cell under an M5 x M6 PG crossing.
# Sourced by grt_pre.tcl (PRE_GLOBAL_ROUTE) when OT_PG_CELL_KEEPOUT=1; grt_post.tcl calls ot_pgcko_remove.
#
# Class (DRT-0255 "maze route cannot find path", GRT overflow 0, deterministic): a cell whose box lies under the crossing
# of an M5 PG pair and an M6 PG pair sits between the M2-M3-M4-M5 PG via stacks of every row and under the M5-M6 via
# array; its pin's only exits are the spacing-dead tracks of the two pairs.  GRT must touch the pin's gcell and lays the
# guide through the M6 row of the pair (PG-TRACK-TRUTH cannot remove that gcell: it holds the pin), so DRT has no path.
# Measured (PG-AWARE-1 probes of 5_1_grt.odb): S81 leaf t69 wire97392, t25 place61109, QC coll_n _25118_/wire35999,
# slw_hc2 wire4487 -- all repair/placement buffers, all with OT_PG_TRACK_TRUTH on where it was on.
#
# Fix: before global_route, a placement blockage over every M5-pair x M6-pair crossing that lies over the rows, then
# detailed_placement moves the (few, sub-um) cells that overlap one; every later repair buffer (GRT repair_design /
# repair_timing) is legalized against the same blockages.  ot_pgcko_remove destroys the blockages before 5_1_grt.odb is
# written (fill, DRT and sign-off see the kit unchanged).  Geometry-generic: reads the PG special wires of the kit.
# OT_PG_CELL_KEEPOUT_MARGIN_UM (default 0) grows each crossing box.  OT_PG_CELL_KEEPOUT=0/unset = off.
proc ot_pgcko_bands {blk ln} {
  # merged PG pair bands of one layer: {lo hi a0 a1} (cross-direction lo..hi, along-direction a0..a1), dbu
  set tech [ord::get_db_tech]; set L [$tech findLayer $ln]
  if {$L eq "NULL"} { return {} }
  set horiz [expr {[$L getDirection] eq "HORIZONTAL"}]
  set iv {}
  foreach net [$blk getNets] {
    if {![$net isSpecial]} continue
    set st [$net getSigType]; if {$st ne "POWER" && $st ne "GROUND"} continue
    foreach sw [$net getSWires] { foreach w [$sw getWires] {
      if {[$w isVia]} continue
      if {[$w getTechLayer] ne $L} continue
      set x0 [$w xMin]; set y0 [$w yMin]; set x1 [$w xMax]; set y1 [$w yMax]
      if {$horiz} { if {$x1-$x0 <= $y1-$y0} continue; lappend iv [list $y0 $y1 $x0 $x1] } \
      else        { if {$y1-$y0 <= $x1-$x0} continue; lappend iv [list $x0 $x1 $y0 $y1] }
    } }
  }
  # merge stripes of one pair (gap below 0.2 um) whose along extents overlap; keep the common along extent
  set gap [expr {round(0.2 * [$tech getDbUnitsPerMicron])}]
  set out {}
  foreach r [lsort -integer -index 0 $iv] {
    lassign $r lo hi a0 a1
    set merged 0
    for {set k [expr {[llength $out]-1}]} {$k >= 0 && $k >= [llength $out]-4} {incr k -1} {
      lassign [lindex $out $k] plo phi pa0 pa1
      if {$lo - $phi < $gap && $a0 < $pa1 && $a1 > $pa0} {
        lset out $k [list $plo [expr {max($phi,$hi)}] [expr {max($pa0,$a0)}] [expr {min($pa1,$a1)}]]
        set merged 1; break
      }
    }
    if {!$merged} { lappend out [list $lo $hi $a0 $a1] }
  }
  return $out
}
proc ot_pgcko_crossings {blk {margin_um 0.0}} {
  # {x0 y0 x1 y1} of every M5-pair x M6-pair crossing (dbu), grown by margin_um
  set dbu [[ord::get_db_tech] getDbUnitsPerMicron]; set m [expr {round($margin_um * $dbu)}]
  set v [ot_pgcko_bands $blk M5]; set h [ot_pgcko_bands $blk M6]
  set h [lsort -integer -index 0 $h]; set hlo {}; foreach b $h { lappend hlo [lindex $b 0] }
  set out {}
  foreach b $v {
    lassign $b x0 x1 vy0 vy1
    # M6 bands whose y band lies inside the M5 band's y extent
    set k [lsearch -sorted -integer -bisect $hlo $vy0]; if {$k < 0} { set k 0 }
    for {} {$k < [llength $h]} {incr k} {
      lassign [lindex $h $k] y0 y1 hx0 hx1
      if {$y0 > $vy1} break
      if {$y1 < $vy0 || $hx1 < $x0 || $hx0 > $x1} continue
      lappend out [list [expr {$x0-$m}] [expr {$y0-$m}] [expr {$x1+$m}] [expr {$y1+$m}]]
    }
  }
  return $out
}
proc ot_pgcko_index {xs} {
  # spatial buckets (4 um) of the crossing boxes: dict "ix,iy" -> list of boxes
  set g 4000; set idx [dict create]
  foreach c $xs { lassign $c x0 y0 x1 y1
    for {set ix [expr {$x0/$g}]} {$ix <= $x1/$g} {incr ix} { for {set iy [expr {$y0/$g}]} {$iy <= $y1/$g} {incr iy} {
      dict lappend idx "$ix,$iy" $c } } }
  return $idx
}
proc ot_pgcko_hit {idx b} {
  # 1 when box b (dbBox) overlaps a crossing of the index
  return [ot_pgcko_box_hit $idx [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
proc ot_pgcko_box_hit {idx bx0 by0 bx1 by1} {
  # 1 when the box overlaps a box of the index (plain numbers: unit-testable without OpenROAD)
  set g 4000
  for {set ix [expr {$bx0/$g}]} {$ix <= $bx1/$g} {incr ix} { for {set iy [expr {$by0/$g}]} {$iy <= $by1/$g} {incr iy} {
    if {![dict exists $idx "$ix,$iy"]} continue
    foreach c [dict get $idx "$ix,$iy"] { lassign $c x0 y0 x1 y1
      if {$bx0 < $x1 && $bx1 > $x0 && $by0 < $y1 && $by1 > $y0} { return 1 } } } }
  return 0
}
proc ot_pgcko_drop_covered {xs fixed_boxes} {
  # DPL-0004 fix (DRT0255-PROOF-1115, k_t49 3,861 TAP cells, kv io_cor 4,071): a placement blockage over a FIXED cell (tapcell, hard
  # row fill) makes ORFS check_placement fail "Placed in rows" after the GRT repair.  Such a cell cannot move, so a crossing it overlaps
  # gets NO blockage (the keepout still covers every crossing over a movable cell).  -> {kept dropped}
  set idx [ot_pgcko_index $fixed_boxes]
  set kept {}; set dropped 0
  foreach c $xs { lassign $c x0 y0 x1 y1
    if {[ot_pgcko_box_hit $idx $x0 $y0 $x1 $y1]} { incr dropped } else { lappend kept $c } }
  return [list $kept $dropped]
}
proc ot_pgcko_fixed_boxes {blk} {
  # boxes of every instance that cannot be moved by detailed_placement: FIXED / LOCKED / FIRM / COVER status, and every tap cell
  set out {}
  foreach i [$blk getInsts] {
    set ms [$i getMaster]; if {[$ms isBlock]} continue
    if {[$i getPlacementStatus] in {FIXED LOCKED FIRM COVER}} { set fx 1 } elseif {[string match CORE_TAPCELL* [$ms getType]]} { set fx 1 } else { set fx 0 }
    if {!$fx} continue
    set b [$i getBBox]; lappend out [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  return $out
}
proc ot_pgcko_add {} {
  if {![info exists ::env(OT_PG_CELL_KEEPOUT)] || $::env(OT_PG_CELL_KEEPOUT) ne "1"} { return }
  if {[info exists ::ot_pgcko_blk] && [llength $::ot_pgcko_blk]} { return }
  set blk [ord::get_db_block]
  set mg 0.0
  if {[info exists ::env(OT_PG_CELL_KEEPOUT_MARGIN_UM)] && $::env(OT_PG_CELL_KEEPOUT_MARGIN_UM) ne ""} { set mg $::env(OT_PG_CELL_KEEPOUT_MARGIN_UM) }
  # rows' bounding box: a crossing outside every row (over a macro, in the core margin) needs no blockage
  set rx0 1e18; set ry0 1e18; set rx1 -1e18; set ry1 -1e18
  foreach r [$blk getRows] { set b [$r getBBox]
    set rx0 [expr {min($rx0,[$b xMin])}]; set ry0 [expr {min($ry0,[$b yMin])}]
    set rx1 [expr {max($rx1,[$b xMax])}]; set ry1 [expr {max($ry1,[$b yMax])}] }
  set ::ot_pgcko_blk {}
  set xs {}
  foreach c [ot_pgcko_crossings $blk $mg] {
    lassign $c x0 y0 x1 y1
    if {$x1 <= $rx0 || $x0 >= $rx1 || $y1 <= $ry0 || $y0 >= $ry1} continue
    lappend xs $c
  }
  # a crossing over a fixed cell (tapcells) gets no blockage: check_placement would fail DPL-0004 on it after the GRT repair
  lassign [ot_pgcko_drop_covered $xs [ot_pgcko_fixed_boxes $blk]] xs ndrop
  foreach c $xs {
    lassign $c x0 y0 x1 y1
    lappend ::ot_pgcko_blk [odb::dbBlockage_create $blk $x0 $y0 $x1 $y1]
  }
  puts "OT_PG_CELL_KEEPOUT skipped $ndrop crossings that lie over fixed cells (tapcells etc.: DPL-0004 'Placed in rows')"
  set idx [ot_pgcko_index $xs]
  # cells that now overlap a blockage: count (movable only; FIXED/LOCKED/FIRM cells stay where they are)
  set n 0; set nfix 0
  foreach i [$blk getInsts] {
    set ms [$i getMaster]; if {[$ms isBlock] || [$ms getType] ne "CORE"} continue
    if {[ot_pgcko_hit $idx [$i getBBox]]} {
      if {[$i getPlacementStatus] in {FIRM LOCKED FIXED COVER}} { incr nfix } else { incr n } }
  }
  puts "OT_PG_CELL_KEEPOUT add [llength $::ot_pgcko_blk] placement blockages (M5 x M6 PG crossings, margin $mg um); cells under them: movable $n fixed $nfix"
  if {$n > 0} {
    # legalize the overlapping cells out of the crossings (others are already legal and stay put)
    # plain detailed_placement, the form ORFS global_route.tcl itself runs after each GRT repair
    set dpl_args {}
    if {[info exists ::env(OT_PG_CELL_KEEPOUT_DPL_ARGS)]} { set dpl_args $::env(OT_PG_CELL_KEEPOUT_DPL_ARGS) }
    detailed_placement {*}$dpl_args
    set left 0
    foreach i [$blk getInsts] {
      set ms [$i getMaster]; if {[$ms isBlock] || [$ms getType] ne "CORE"} continue
      if {[$i getPlacementStatus] in {FIRM LOCKED FIXED COVER}} continue
      if {[ot_pgcko_hit $idx [$i getBBox]]} { incr left }
    }
    puts "OT_PG_CELL_KEEPOUT after detailed_placement: movable cells under a crossing $left"
  }
}
proc ot_pgcko_remove {} {
  if {![info exists ::ot_pgcko_blk] || ![llength $::ot_pgcko_blk]} { return }
  foreach b $::ot_pgcko_blk { odb::dbBlockage_destroy $b }
  puts "OT_PG_CELL_KEEPOUT removed [llength $::ot_pgcko_blk] placement blockages before 5_1_grt.odb is written"
  set ::ot_pgcko_blk {}
}
