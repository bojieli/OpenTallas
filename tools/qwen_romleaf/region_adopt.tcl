# Q-A0FIX (2026-10-19): EXCLUSIVE parent regions adopt the movable cells that sit inside them before every
# detailed_placement call of the stage (sourced from a kit's PRE_DETAIL_PLACE / PRE_CTS / PRE_GLOBAL_ROUTE hook).
#
# Why: tools/qwen_romleaf/parent_regions.tcl groups only the region's REGISTERS.  RePlAce treats an EXCLUSIVE box as
# soft for ungrouped cells, so the registers' own combinational logic lands inside the box (NL c1r9d 3_5: 235 ungrouped
# cells inside the 60 x 60 um hub box, e.g. _35608_ at (384.2, 419.9) = box centre), and every buffer inserted later
# (CTS root clkbuf_0_ck at the hub sink centroid, repair_timing hold buffers on hub paths) is ungrouped too.  DPL must
# then move each of them OUT of the box, but the box centre is 30 um from every edge, beyond the legalizer window
# (+/-500 sites = 27 um, +/-100 rows = 27 um): the cells stay stuck and overlap (gate c1r9d 10-18 18:38 ot-epyc4:
# DPL-0701 37 cells, DPL-0033 clkbuf_0_ck/_35608_, hold43688/_28559_ ...).
#
# Fix (region-aware insertion): a movable standard cell whose centre lies inside an EXCLUSIVE qrl_* box becomes a
# member of that box's group, so it legalizes on the region's own free sites (hub flop fill ~23 %) instead of being
# expelled across the box.  Fixed cells (taps, end caps, pin flops placed FIRM/FIXED), hard macros and already-grouped
# cells are untouched; no check is relaxed (ORFS check_placement still runs after the last pass).
proc ::qrl_adopt_region_cells {} {
  set block [ord::get_db_block]
  set boxes {}
  foreach r [$block getRegions] {
    if {![string match qrl_* [$r getName]]} continue
    if {[$r getRegionType] ne "EXCLUSIVE"} continue
    set g [$block findGroup [$r getName]]
    if {$g eq "NULL" || $g eq ""} continue
    foreach bx [$r getBoundaries] { lappend boxes [list [$bx xMin] [$bx yMin] [$bx xMax] [$bx yMax] $g [$r getName]] }
  }
  if {![llength $boxes]} { puts "QRL_ADOPT: no EXCLUSIVE qrl regions"; return }
  set n [dict create]
  foreach i [$block getInsts] {
    set gi [$i getGroup]
    if {$gi ne "NULL" && $gi ne ""} continue
    if {[[$i getMaster] isBlock]} continue
    if {[$i isFixed]} continue
    if {![$i isPlaced]} continue
    set bb [$i getBBox]
    set cx [expr {([$bb xMin] + [$bb xMax]) / 2}]
    set cy [expr {([$bb yMin] + [$bb yMax]) / 2}]
    foreach b $boxes {
      lassign $b x0 y0 x1 y1 g rn
      if {$cx > $x0 && $cx < $x1 && $cy > $y0 && $cy < $y1} {
        $g addInst $i
        dict incr n $rn
        break
      }
    }
  }
  puts "QRL_ADOPT: [expr {[dict size $n] ? $n : {none}}]"
}
if {[llength [info commands ::ot_qrl_adopt_dpl_orig]] == 0} {
  rename detailed_placement ::ot_qrl_adopt_dpl_orig
  proc detailed_placement {args} {
    ::qrl_adopt_region_cells
    ::ot_qrl_adopt_dpl_orig {*}$args
  }
}
