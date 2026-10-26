# Macro-to-macro CHANNEL blocking for hard-macro parents (POST_IO_PLACEMENT hook; spec orfs_vars
# POST_IO_PLACEMENT_TCL=physical/common_flow/macro_channel_block.tcl, OT_CHANNEL_BLOCK_UM=<um>, default 20).
# Root cause (Q-COMPUTE-ELEM r13, 2026-10-15, qfd_tile_nk_banked_v1 bp58b EPYC1TB qfd_tile_nk_banked_v1-20261015-042621):
# 83 hard children packed with 144 macro channels narrower than the 20 um production rule (min 5.184 um) kept
# placement rows; GPL / repair_design buffers landed in those slivers and DPL failed ("detail_place.tcl, 39 bad
# optional access", the edge_sliver_block.tcl signature).  The production rule (tools/textbook_lint.py util_channel)
# is ">= 20 um or block the channel": this hook blocks every macro-to-macro gap < OT_CHANNEL_BLOCK_UM with a HARD
# placement blockage over the pair's facing overlap extended by the same distance (staggered pairs), and removes the
# tap / endcap cells inside (a fixed cell under a hard blockage fails DPL-0004 / DPL-0033).  Routing is untouched.
# It runs at POST_IO_PLACEMENT so 3_2_place_iop.odb (the ODB the pre-route gate's textbook lint dumps) carries the
# blockages.  Same algorithm as physical/hbm_attn_tile_r/die_tile/sliver_block.tcl (attn-tile-2, 2026-10-08).
if {![info exists ot_sliver_um]} {
  set ot_sliver_um 20.0
  if {[info exists ::env(OT_CHANNEL_BLOCK_UM)] && $::env(OT_CHANNEL_BLOCK_UM) ne ""} { set ot_sliver_um $::env(OT_CHANNEL_BLOCK_UM) }
}
set ot_blk [ord::get_db_block]
set ot_dbu [$ot_blk getDbUnitsPerMicron]
set ot_t [expr {int($ot_sliver_um * $ot_dbu)}]
set ot_die [$ot_blk getDieArea]
set ot_bbs {}
foreach ot_i [$ot_blk getInsts] {
  if {![[$ot_i getMaster] isBlock]} {continue}
  set b [$ot_i getBBox]
  lappend ot_bbs [list [$b xMin] [$b yMin] [$b xMax] [$b yMax]]
}
set ot_nb 0
set ot_rects {}
set ot_area 0.0
set ot_n [llength $ot_bbs]
for {set i 0} {$i < $ot_n} {incr i} {
  lassign [lindex $ot_bbs $i] ax0 ay0 ax1 ay1
  for {set j [expr {$i + 1}]} {$j < $ot_n} {incr j} {
    lassign [lindex $ot_bbs $j] bx0 by0 bx1 by1
    set ox [expr {min($ax1, $bx1) - max($ax0, $bx0)}]
    set oy [expr {min($ay1, $by1) - max($ay0, $by0)}]
    set r {}
    if {$ox > -$ot_t && $oy < 0 && -$oy < $ot_t} {
      # vertical gap (stacked banks): block the gap rows over the x overlap widened by T
      set r [list [expr {max(max($ax0, $bx0) - $ot_t, [$ot_die xMin])}] [expr {min($ay1, $by1)}] \
                  [expr {min(min($ax1, $bx1) + $ot_t, [$ot_die xMax])}] [expr {max($ay0, $by0)}]]
    } elseif {$oy > -$ot_t && $ox < 0 && -$ox < $ot_t} {
      set r [list [expr {min($ax1, $bx1)}] [expr {max(max($ay0, $by0) - $ot_t, [$ot_die yMin])}] \
                  [expr {max($ax0, $bx0)}] [expr {min(min($ay1, $by1) + $ot_t, [$ot_die yMax])}]]
    }
    if {$r eq {}} {continue}
    lassign $r x0 y0 x1 y1
    if {$x1 <= $x0 || $y1 <= $y0} {continue}
    odb::dbBlockage_create $ot_blk $x0 $y0 $x1 $y1
    lappend ot_rects [list $x0 $y0 $x1 $y1]
    incr ot_nb
    set ot_area [expr {$ot_area + ($x1 - $x0) / double($ot_dbu) * ($y1 - $y0) / double($ot_dbu)}]
  }
}
# tapcell / endcap instances (fixed, physical only) inside a blocked sliver would fail check_placement's "placed in
# rows" test; no logic can sit in the sliver, so its taps and row-end caps go with it.
set ot_rm 0
foreach ot_i [$ot_blk getInsts] {
  set ot_ty [[$ot_i getMaster] getType]
  if {![string match "CORE_WELLTAP" $ot_ty] && ![string match "ENDCAP*" $ot_ty] && \
      ![string match "TAP_*" [$ot_i getName]] && ![string match "PHY_EDGE_*" [$ot_i getName]]} {continue}
  set b [$ot_i getBBox]
  set cx0 [$b xMin]; set cy0 [$b yMin]; set cx1 [$b xMax]; set cy1 [$b yMax]
  foreach ot_r $ot_rects {
    lassign $ot_r x0 y0 x1 y1
    if {$cx0 < $x1 && $cx1 > $x0 && $cy0 < $y1 && $cy1 > $y0} { odb::dbInst_destroy $ot_i; incr ot_rm; break }
  }
}
puts "OT_SLIVER_PHYS_REMOVED $ot_rm"
puts [format "OT_SLIVER_BLOCKAGES %d (gap < %.1f um, %.1f um^2)" $ot_nb $ot_sliver_um $ot_area]
# Row slivers: tapcell's 2 um macro halo leaves 1.2-3 um row segments between a macro and the core edge or between
# two macros (bp58b rows 2491..2585 x 478.33-479.52, 29.05-30.35 ...).  They hold only their own endcaps; the
# negotiation legaliser parks wide repair buffers (BUFx16f) on them and cannot recover (exp2: 14 DPL-0033 overlaps
# with PHY_EDGE_ROW_*_Right endcaps).  Every row segment shorter than OT_ROW_MIN_UM (default 6 um) is removed with
# the physical cells on it; no logic cell can use such a segment anyway.
set ot_rmin 6.0
if {[info exists ::env(OT_ROW_MIN_UM)] && $::env(OT_ROW_MIN_UM) ne ""} { set ot_rmin $::env(OT_ROW_MIN_UM) }
set ot_rminu [expr {int($ot_rmin * $ot_dbu)}]
set ot_short {}
set ot_sy [dict create]
foreach ot_r [$ot_blk getRows] {
  set ot_bb [$ot_r getBBox]
  if {[$ot_bb xMax] - [$ot_bb xMin] < $ot_rminu} {
    lappend ot_short $ot_r
    dict lappend ot_sy [$ot_bb yMin] [list [$ot_bb xMin] [$ot_bb xMax]]
  }
}
set ot_srm 0
if {[llength $ot_short] > 0} {
  # physical cells sit on exactly one row: look the short segments up by the cell's yMin (no pair scan)
  foreach ot_i [$ot_blk getInsts] {
    set ot_ty [[$ot_i getMaster] getType]
    if {![string match "CORE_WELLTAP" $ot_ty] && ![string match "ENDCAP*" $ot_ty] && \
        ![string match "TAP_*" [$ot_i getName]] && ![string match "PHY_EDGE_*" [$ot_i getName]]} {continue}
    set b [$ot_i getBBox]
    if {![dict exists $ot_sy [$b yMin]]} {continue}
    set cx [expr {([$b xMin] + [$b xMax]) / 2}]
    foreach ot_s [dict get $ot_sy [$b yMin]] {
      lassign $ot_s x0 x1
      if {$cx >= $x0 && $cx < $x1} { odb::dbInst_destroy $ot_i; incr ot_srm; break }
    }
  }
  foreach ot_r $ot_short { odb::dbRow_destroy $ot_r }
}
puts [format "OT_ROW_SLIVERS removed %d row segments < %.1f um and %d physical cells on them" [llength $ot_short] $ot_rmin $ot_srm]
