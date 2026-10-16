# drive-0849: copy for HBM die views (route_view.sh extra arg --step-tcl POST_PDN=physical/hbm_accel_die_views/common/sliver_block.tcl); hfd_coll srcdc3 rx[3]/rx[6] SRAM gap 6.07 um
# S81-PH tile copy (drive-2125 2026-10-08, template F): from physical/hbm_attn_tile_r/die_tile/sliver_block.tcl, sourced as a POST_PDN step hook
# (route_view.sh extra arg --step-tcl POST_PDN=...); ot_sliver_um defaults to 12.0.  dsfd_colt_lane: u_q.g_m[0].u_m | g_m[1].u_m gap 10.78 um.
# Sliver blockages for the bank-built HBM attention die tile (appended to the POST_PDN hook by route_dt_cl.sh when
# SLIVER is set; route_dt_cl.sh prepends "set ot_sliver_um <um>").
# Root cause (attn-tile-2, 2026-10-08): the pin-bank stacks sit 1.5-3.6 um apart (macro edge to edge).  With the 1 um
# row halo each gap leaves a 2-5 row strip of legal sites between two banks.  Global placement and repair_design's
# wire buffers pile cells into those strips (r23h: 30 BUFx* at x 1113-1139 / y 807.3 between banks 794.18-806.06 and
# 809.30-821.18; r23hq: 112 cells at x 850-925 / y 551.3 between banks 538.20-550.08 and 553.42-565.30, plus 2 cells in
# a 2.44 um vertical gap at x 942) and the detail placer cannot legalise them -> DPL-0033.
# Fix: a hard placement blockage over every macro-to-macro gap narrower than ot_sliver_um, over the pair's facing
# overlap extended by ot_sliver_um on each side (catches staggered pairs).  Routing is untouched: only std-cell
# placement leaves the slivers; the cells land in the open floor next to the stack.
if {![info exists ot_sliver_um]} { set ot_sliver_um 12.0 }
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
