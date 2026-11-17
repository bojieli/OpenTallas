# cts_trunk_reseat.tcl -- FABLE-FIX-S81-IFN0-HW 2026-11-16: seat every CTS trunk buffer at the centroid of its loads.
#
# Evidence (S81 rom_q half hw_splitbal1, 2 ROM macros 125x63 um stacked in the core centre, sinks in a ring around
# them): TritonCTS places the buffer of a trunk segment at the H-tree point two levels up.  Where that point lies on a
# macro it is pushed to the macro edge / the channel between the macros, and the buffer then drives ALL its leaf
# buffers through one 100-150 um net (clkbuf_6_55: 14 BUFx24 leaves at y 200-215 from (173,114); 67 fF routed, slew
# 521 ps at the leaf inputs, leaf stage 230.6 ps; the acc_r captures 230 ps late, related-pair skew 264 ps).
# The load cap sits at the FAR end of the resistive wire: delay ~ R_wire * (C_wire/2 + n_leaves * C_in).
#
# Fix at the structure: bottom-up, each CTS trunk buffer (clkbuf_<level>_...) whose loads' centroid is further than
# OT_CTS_RESEAT_MIN_UM (25) away is moved to that centroid (kept off macros + OT_CTS_RESEAT_HALO_UM), its dummy loads
# follow.  The long wire moves up to the parent net, where the far end carries one buffer input per sibling instead
# of every leaf: point-to-point trunk into the region, local distribution inside it.  No cell added or removed, no net
# changed, clock ancestry untouched; the detailed placement that follows CTS legalizes the moved cells.
# Installed as a clock_tree_synthesis wrapper (same form as macro_cts_cluster.tcl).  Opt-in: OT_CTS_TRUNK_RESEAT=1.
proc ot_ctr_env {k d} {
  if {[info exists ::env($k)] && $::env($k) ne ""} { return $::env($k) }
  return $d
}
proc ot_ctr_center {i} { set b [$i getBBox]; return [list [expr {([$b xMin]+[$b xMax])/2}] [expr {([$b yMin]+[$b yMax])/2}]] }
# load position: the pin shape for a macro (its centre is not its clock pin), the cell centre otherwise
proc ot_ctr_pin_xy {t} {
  set i [$t getInst]
  if {[[$i getMaster] isBlock]} {
    set r [$t getAvgXY]
    if {[llength $r] == 3 && [lindex $r 0]} { return [lrange $r 1 2] }
  }
  return [ot_ctr_center $i]
}
proc ot_ctr_is_trunk {i} { return [regexp {^clkbuf_[0-9]+_} [$i getName]] }
proc ot_ctr_out_net {i} {
  foreach t [$i getITerms] { if {[$t isOutputSignal] && [$t getNet] ne "NULL"} { return [$t getNet] } }
  return ""
}
proc ot_ctr_driver {i} {
  foreach t [$i getITerms] {
    if {![$t isInputSignal] || [$t getNet] eq "NULL"} continue
    foreach d [[$t getNet] getITerms] { if {[$d isOutputSignal]} { return [$d getInst] } }
  }
  return ""
}
# nearest point outside every blocked rect (rects already expanded by the halo), inside the core
proc ot_ctr_legal {x y} {
  global ot_ctr_rects ot_ctr_core
  lassign $ot_ctr_core cx0 cy0 cx1 cy1
  for {set pass 0} {$pass < 4} {incr pass} {
    set hit 0
    foreach r $ot_ctr_rects {
      lassign $r x0 y0 x1 y1
      if {$x <= $x0 || $x >= $x1 || $y <= $y0 || $y >= $y1} continue
      set hit 1; set best ""
      foreach {d nx ny} [list [expr {$x-$x0}] $x0 $y [expr {$x1-$x}] $x1 $y [expr {$y-$y0}] $x $y0 [expr {$y1-$y}] $x $y1] {
        if {$nx < $cx0 || $nx > $cx1 || $ny < $cy0 || $ny > $cy1} continue
        if {$best eq "" || $d < [lindex $best 0]} { set best [list $d $nx $ny] }
      }
      if {$best eq ""} { return "" }
      set x [lindex $best 1]; set y [lindex $best 2]
    }
    if {!$hit} break
  }
  return [list [expr {max($cx0,min($cx1,$x))}] [expr {max($cy0,min($cy1,$y))}]]
}
proc ot_ctr_visit {i} {
  global ot_ctr_seen ot_ctr_min ot_ctr_moves ot_ctr_n ot_ctr_dbu
  if {[dict exists $ot_ctr_seen $i]} return
  dict set ot_ctr_seen $i 1
  set on [ot_ctr_out_net $i]; if {$on eq ""} return
  set loads {}; set dummies {}
  foreach t [$on getITerms] {
    if {![$t isInputSignal]} continue
    set l [$t getInst]
    if {[string match clkload* [$l getName]]} { lappend dummies $l; continue }
    if {[ot_ctr_is_trunk $l]} { ot_ctr_visit $l }
    lappend loads $t
  }
  incr ot_ctr_n
  if {![llength $loads]} return
  set d [ot_ctr_driver $i]
  # the first buffer of a tree stays at its source (its input wire is driven by a gate / port, not by a CTS buffer)
  if {$d eq "" || ![string match clkbuf_* [$d getName]]} return
  if {[$i isFixed] || [$i isDoNotTouch]} return
  set sx 0; set sy 0
  foreach t $loads { lassign [ot_ctr_pin_xy $t] x y; set sx [expr {$sx+$x}]; set sy [expr {$sy+$y}] }
  set tx [expr {$sx/[llength $loads]}]; set ty [expr {$sy/[llength $loads]}]
  lassign [ot_ctr_center $i] bx by
  if {abs($tx-$bx)+abs($ty-$by) <= $ot_ctr_min} return
  set p [ot_ctr_legal $tx $ty]; if {$p eq ""} return
  lassign $p tx ty
  set dist [expr {abs($tx-$bx)+abs($ty-$by)}]
  if {$dist <= $ot_ctr_min} return
  set bb [$i getBBox]
  $i setLocation [expr {$tx-([$bb xMax]-[$bb xMin])/2}] [expr {$ty-([$bb yMax]-[$bb yMin])/2}]
  $i setPlacementStatus PLACED
  foreach l $dummies {
    if {[$l isFixed]} continue
    lassign [ot_ctr_center $l] x y
    $l setLocation [expr {[lindex [$l getLocation] 0]+$tx-$bx}] [expr {[lindex [$l getLocation] 1]+$ty-$by}]
    $l setPlacementStatus PLACED
  }
  lappend ot_ctr_moves [list [$i getName] [expr {$bx/$ot_ctr_dbu}] [expr {$by/$ot_ctr_dbu}] [expr {$tx/$ot_ctr_dbu}] [expr {$ty/$ot_ctr_dbu}] [expr {$dist/$ot_ctr_dbu}] [llength $loads]]
}
proc ot_ctr_run {} {
  global ot_ctr_seen ot_ctr_min ot_ctr_moves ot_ctr_n ot_ctr_dbu ot_ctr_rects ot_ctr_core
  set blk [ord::get_db_block]
  set ot_ctr_dbu [expr {double([$blk getDbUnitsPerMicron])}]
  set ot_ctr_min [expr {int([ot_ctr_env OT_CTS_RESEAT_MIN_UM 25]*$ot_ctr_dbu)}]
  set halo [expr {int([ot_ctr_env OT_CTS_RESEAT_HALO_UM 6]*$ot_ctr_dbu)}]
  set ca [$blk getCoreArea]
  set ot_ctr_core [list [$ca xMin] [$ca yMin] [$ca xMax] [$ca yMax]]
  set ot_ctr_rects {}
  foreach i [$blk getInsts] {
    if {![[$i getMaster] isBlock]} continue
    set b [$i getBBox]
    lappend ot_ctr_rects [list [expr {[$b xMin]-$halo}] [expr {[$b yMin]-$halo}] [expr {[$b xMax]+$halo}] [expr {[$b yMax]+$halo}]]
  }
  foreach bk [$blk getBlockages] {
    if {[$bk isSoft]} continue
    set b [$bk getBBox]
    lappend ot_ctr_rects [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
  }
  set ot_ctr_seen [dict create]; set ot_ctr_moves {}; set ot_ctr_n 0
  foreach i [$blk getInsts] { if {[ot_ctr_is_trunk $i]} { ot_ctr_visit $i } }
  set mx 0
  foreach m $ot_ctr_moves {
    lassign $m nm bx by tx ty dist nl
    if {$dist > $mx} { set mx $dist }
    puts [format "OT_CTS_RESEAT move %s (%.1f,%.1f) -> (%.1f,%.1f) %.1f um loads %d" $nm $bx $by $tx $ty $dist $nl]
  }
  puts [format "OT_CTS_RESEAT moved %d of %d trunk buffers (min %.0f um, %d blocked rects), max move %.1f um" [llength $ot_ctr_moves] $ot_ctr_n [expr {$ot_ctr_min/$ot_ctr_dbu}] [llength $ot_ctr_rects] $mx]
}
if {[ot_ctr_env OT_CTS_TRUNK_RESEAT 0] eq "1" && [info commands clock_tree_synthesis] ne "" && [info commands ot_ctr_cts_orig] eq ""} {
  rename clock_tree_synthesis ot_ctr_cts_orig
  proc clock_tree_synthesis {args} {
    set r [uplevel 1 [list ot_ctr_cts_orig {*}$args]]
    ot_ctr_run
    return $r
  }
  puts "OT_CTS_RESEAT armed (OT_CTS_TRUNK_RESEAT=1)"
}
