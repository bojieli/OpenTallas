# SRAM vertical-edge M5 no-entry strip for dsfd_coll_lane_w (cxea3, claude ds-coll 2026-10-13); the hrow5 r8 hook
# (physical/hrow_cx/sram_edge_access.tcl) on this tile's macro: hrow5_cbe_cx r8a routed DRC 0 with it (r7 was 21).
# Routed evidence here (cxea2-efb 5_route_drc.rpt, DRC 7 = 6 M4 Short + 1 M4 spacing): every marker is an M4 stub
# x 205.237..205.584 (u_rb E edge 205.584) or 399.541..399.984 (u_fifo E edge 399.984): the stub runs from the
# first M5 track past the old 0.30 um guard (sram_edge_access.tcl) across the macro M4 OBS to the E-edge pin.
# The 0.30 um guard only moved the VIA45 drop deeper (21 -> 7).  Contract now: M5 over an SRAM is N-S pass-through
# only; a strip-wide band inside each vertical macro edge has no M5, the M4 edge pins are reached planar from the
# channel and VIA45 lands outside the macro.  Created pre-GRT, removed post-DRT (the abstract carries real metal).
set cx_strip_um [expr {[info exists ::env(OT_CX_COLL_STRIP_UM)] ? $::env(OT_CX_COLL_STRIP_UM) : 6.0}]
set cx_caller [dict get [info frame -1] file]
set cx_stage [file tail $cx_caller]
puts "CX_COLL SRAM hook invoked caller=$cx_stage"
if {[string match *pre_grt.tcl $cx_stage] || [string match *post_drt.tcl $cx_stage]} {
  set b [ord::get_db_block]
  set t [[ord::get_db] getTech]
  set u [$b getDbUnitsPerMicron]
  set rects {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMax]-round($cx_strip_um*$u)}] [$r yMin] [expr {[$r xMax]-round(0.024*$u)}] [$r yMax]]
  }
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_512x128_m4_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMin]+round(0.024*$u)}] [$r yMin] [expr {[$r xMin]+round($cx_strip_um*$u)}] [$r yMax]]
  }
  set count 0
  if {[string match *pre_grt.tcl $cx_stage]} {
    foreach r $rects { odb::dbObstruction_create $b [$t findLayer M5] {*}$r; incr count }
    if {$count != 20} { error "CX_COLL expected 20 guards, created $count" }
    puts "CX_COLL SRAM access keepout created $count strip $cx_strip_um um"
  } else {
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M5"} continue
      set k [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {[lsearch -exact $rects $k] >= 0} { odb::dbObstruction_destroy $o; incr count }
    }
    if {$count != 20} { error "CX_COLL expected 20 guards, removed $count" }
    puts "CX_COLL SRAM access keepout removed $count"
  }
}
