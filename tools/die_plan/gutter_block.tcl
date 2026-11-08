# GENERATED copy of tools/die_plan/gutter_block.tcl (sourced at the end of face_flops.tcl, PRE_GLOBAL_PLACE, after
# relay_mid.tcl).  NARROW-GUTTER class (S81-TYPES-5 11-07, COORD 15:3x t56 smell + COLH10 e10 channels): GPL put
# high-fanout drivers (vp_cf native_memory words, fanout 5 over 925 um of LN macros; vp_rr rst_n fanout 53) and relay
# clusters into the 6-40 um gutters between macro columns, because a gutter is the centroid of the macro pins on both
# sides.  The gutter then has no room for the wires that must pass it.  Opt-in OT_GUTTER_BLOCK_UM=<G> (default off = no
# file effect): every gap narrower than G between two facing macros (overlapping span on the other axis) gets a hard
# placement blockage over the gap, so soft logic lands on the open side of the macro row/column.  Routing is unchanged
# (placement blockage only).  FIRM / LOCKED cells already in a gutter (landing rings, plan stations) are not moved; a
# released FIRM cell is legalised out of the gutter by DPL.  Gaps along the core edge are left alone (pin access).
uplevel #0 {
if {[info exists ::env(OT_GUTTER_BLOCK_UM)] && $::env(OT_GUTTER_BLOCK_UM) > 0} {
  set gb_blk [ord::get_db_block]
  set gb_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set gb_g [expr {int($::env(OT_GUTTER_BLOCK_UM) * $gb_dbu)}]
  set gb_min [expr {int(0.27 * $gb_dbu)}]
  # S81-TYPES-7-COLH 11-08: OT_GUTTER_BLOCK_MIN_SPAN_UM (opt-in) = only gaps facing over at least this span
  if {[info exists ::env(OT_GUTTER_BLOCK_MIN_SPAN_UM)] && $::env(OT_GUTTER_BLOCK_MIN_SPAN_UM) > 0} {
    set gb_min [expr {max($gb_min, int($::env(OT_GUTTER_BLOCK_MIN_SPAN_UM) * $gb_dbu))}]
  }
  set gb_m {}
  foreach i [$gb_blk getInsts] {
    if {[[$i getMaster] isBlock]} { set b [$i getBBox]; lappend gb_m [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]] }
  }
  set gb_n 0; set gb_area 0.0
  set gb_rects {}
  set n [llength $gb_m]
  for {set a 0} {$a < $n} {incr a} {
    lassign [lindex $gb_m $a] ax0 ay0 ax1 ay1
    for {set b 0} {$b < $n} {incr b} {
      if {$a == $b} continue
      lassign [lindex $gb_m $b] bx0 by0 bx1 by1
      # vertical gutter: b right of a, y spans overlap
      set gx [expr {$bx0 - $ax1}]
      set oy0 [expr {max($ay0, $by0)}]; set oy1 [expr {min($ay1, $by1)}]
      if {$gx > 0 && $gx < $gb_g && $oy1 - $oy0 > $gb_min} {
        set clear 1
        foreach m $gb_m { lassign $m mx0 my0 mx1 my1
          if {$mx0 < $bx0 && $mx1 > $ax1 && $my0 < $oy1 && $my1 > $oy0} { set clear 0; break } }
        if {$clear} { lappend gb_rects [list $ax1 $oy0 $bx0 $oy1] }
      }
      # horizontal gutter: b above a, x spans overlap
      set gy [expr {$by0 - $ay1}]
      set ox0 [expr {max($ax0, $bx0)}]; set ox1 [expr {min($ax1, $bx1)}]
      if {$gy > 0 && $gy < $gb_g && $ox1 - $ox0 > $gb_min} {
        set clear 1
        foreach m $gb_m { lassign $m mx0 my0 mx1 my1
          if {$my0 < $by0 && $my1 > $ay1 && $mx0 < $ox1 && $mx1 > $ox0} { set clear 0; break } }
        if {$clear} { lappend gb_rects [list $ox0 $ay1 $ox1 $by0] }
      }
    }
  }
  set gb_log [open $::env(RESULTS_DIR)/ot_gutter_block.txt w]
  foreach r $gb_rects {
    lassign $r x0 y0 x1 y1
    odb::dbBlockage_create $gb_blk $x0 $y0 $x1 $y1
    incr gb_n
    set gb_area [expr {$gb_area + ($x1 - $x0) * ($y1 - $y0) / double($gb_dbu * $gb_dbu)}]
    puts $gb_log "[expr {$x0 / double($gb_dbu)}]\t[expr {$y0 / double($gb_dbu)}]\t[expr {$x1 / double($gb_dbu)}]\t[expr {$y1 / double($gb_dbu)}]"
  }
  close $gb_log
  puts "OT_GUTTER_BLOCK $gb_n gutter placement blockages (gap < $::env(OT_GUTTER_BLOCK_UM) um between facing macros), [format %.1f $gb_area] um2"
}
}
