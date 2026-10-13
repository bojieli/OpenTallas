# SRAM vertical-edge M5 no-entry strip for ot_s81_hc_crooty_y (cryy v5, s81hc-1013 r6, 2026-10-13): the hrow5 r8 hook
# (physical/hrow_cx/sram_edge_access.tcl; hrow5_cbe_cx r8a routed DRC 0 with it, r7 was 21) on this tile's 11
# ot_sram_1r1w_128x256_m1_r2c2 macros.  The macro's pins are M4 stubs 0.024 um wide on its W / E edges and the LEF
# OBS covers M1-M4 from 0.072 um in, so M5 over the macro can only pass N-S: a VIA45 drop inside the macro edge lands
# on M4 OBS.  Global route does not know that and books the M5 tracks just inside each vertical macro edge as pin
# access for the 411 (W face) / 153+ (E face) pin nets, which is what it leaned on beside the W edge channel in
# v3 / v4.  Contract: a strip-wide band inside each vertical macro edge carries no M5 at all (global and detailed
# route); the edge pins are reached planar on M4 from the channel and VIA45 lands outside the macro.  M5 further in is
# N-S pass-through (reached over M6).  Created pre-GRT, removed post-DRT (the abstract carries only real metal).
set cy_strip_um [expr {[info exists ::env(OT_CRYY_STRIP_UM)] ? $::env(OT_CRYY_STRIP_UM) : 6.0}]
set cy_master ot_sram_1r1w_128x256_m1_r2c2
set cy_expect 22
set cy_caller [dict get [info frame -1] file]
set cy_stage [file tail $cy_caller]
puts "CRYY SRAM hook invoked caller=$cy_stage"
if {[string match *pre_grt.tcl $cy_stage] || [string match *post_drt.tcl $cy_stage]} {
  set b [ord::get_db_block]
  set t [[ord::get_db] getTech]
  set u [$b getDbUnitsPerMicron]
  set rects {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne $cy_master} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMax]-round($cy_strip_um*$u)}] [$r yMin] [expr {[$r xMax]-round(0.024*$u)}] [$r yMax]]
    lappend rects [list [expr {[$r xMin]+round(0.024*$u)}] [$r yMin] [expr {[$r xMin]+round($cy_strip_um*$u)}] [$r yMax]]
  }
  set count 0
  if {[string match *pre_grt.tcl $cy_stage]} {
    foreach r $rects { odb::dbObstruction_create $b [$t findLayer M5] {*}$r; incr count }
    if {$count != $cy_expect} { error "CRYY expected $cy_expect guards, created $count" }
    puts "CRYY SRAM access keepout created $count strip $cy_strip_um um"
  } else {
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M5"} continue
      set k [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {[lsearch -exact $rects $k] >= 0} { odb::dbObstruction_destroy $o; incr count }
    }
    if {$count != $cy_expect} { error "CRYY expected $cy_expect guards, removed $count" }
    puts "CRYY SRAM access keepout removed $count"
  }
}
