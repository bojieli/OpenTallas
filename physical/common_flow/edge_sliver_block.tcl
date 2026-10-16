# struct-close 2026-10-09: CORE-EDGE sliver blockages (PRE_GLOBAL_PLACE hook; macros are placed by then).
# Root cause (ot_hbm_norm_engine_view, 6+ calibrate "synth_or_place" fails): the macro placer stacks the mem1 SRAMs
# against the core edge (u_x column at x 1003.2-1098.0 in a core ending at 1102); the 4 um halo leaves a < 1 row-width
# strip between the stack and the core edge.  repair_design's wire buffers land there, DPL reports edge-spacing
# violations (36), then crashes ("detail_place.tcl, 39 bad optional access").  Fix: a hard placement blockage over
# every macro-to-CORE-EDGE gap narrower than ot_edge_sliver_um (default 12), along the macro's extent; taps / endcaps in
# a blocked strip go with it (as physical/hbm_attn_tile_r/die_tile/sliver_block.tcl).  Routing untouched.
if {![info exists ot_edge_sliver_um]} {
  set ot_edge_sliver_um [expr {[info exists ::env(OT_EDGE_SLIVER_UM)] ? $::env(OT_EDGE_SLIVER_UM) : 12.0}]
}
set ot_blk [ord::get_db_block]
set ot_dbu [$ot_blk getDbUnitsPerMicron]
set ot_t [expr {int($ot_edge_sliver_um * $ot_dbu)}]
set ot_core [$ot_blk getCoreArea]
set cx0 [$ot_core xMin]; set cy0 [$ot_core yMin]; set cx1 [$ot_core xMax]; set cy1 [$ot_core yMax]
set ot_rects {}; set ot_area 0.0
foreach ot_i [$ot_blk getInsts] {
  if {![[$ot_i getMaster] isBlock]} {continue}
  set b [$ot_i getBBox]
  set x0 [$b xMin]; set y0 [$b yMin]; set x1 [$b xMax]; set y1 [$b yMax]
  set r {}
  if {$cx1 - $x1 > 0 && $cx1 - $x1 < $ot_t} { lappend r [list $x1 $y0 $cx1 $y1] }
  if {$x0 - $cx0 > 0 && $x0 - $cx0 < $ot_t} { lappend r [list $cx0 $y0 $x0 $y1] }
  if {$cy1 - $y1 > 0 && $cy1 - $y1 < $ot_t} { lappend r [list $x0 $y1 $x1 $cy1] }
  if {$y0 - $cy0 > 0 && $y0 - $cy0 < $ot_t} { lappend r [list $x0 $cy0 $x1 $y0] }
  foreach q $r {
    lassign $q a0 b0 a1 b1
    odb::dbBlockage_create $ot_blk $a0 $b0 $a1 $b1
    lappend ot_rects $q
    set ot_area [expr {$ot_area + ($a1 - $a0) / double($ot_dbu) * ($b1 - $b0) / double($ot_dbu)}]
  }
}
# stacked macros leave the strips between their edge blockages: merge by also blocking each strip's full extent between
# two vertically / horizontally adjacent edge strips is unnecessary (a strip between two macros of one column is a
# macro-to-macro gap, handled by the halo).  Physical-only cells inside a blocked strip:
set ot_rm 0
foreach ot_i [$ot_blk getInsts] {
  set ot_ty [[$ot_i getMaster] getType]
  if {![string match "CORE_WELLTAP" $ot_ty] && ![string match "ENDCAP*" $ot_ty] && \
      ![string match "TAP_*" [$ot_i getName]] && ![string match "PHY_EDGE_*" [$ot_i getName]]} {continue}
  set b [$ot_i getBBox]
  set ix0 [$b xMin]; set iy0 [$b yMin]; set ix1 [$b xMax]; set iy1 [$b yMax]
  foreach q $ot_rects {
    lassign $q a0 b0 a1 b1
    if {$ix0 < $a1 && $ix1 > $a0 && $iy0 < $b1 && $iy1 > $b0} { odb::dbInst_destroy $ot_i; incr ot_rm; break }
  }
}
puts [format "OT_EDGE_SLIVER_BLOCKAGES %d (macro-to-core-edge gap < %.1f um, %.1f um^2), physical cells removed %d" [llength $ot_rects] $ot_edge_sliver_um $ot_area $ot_rm]
