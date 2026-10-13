# SRAM vertical-edge M5 no-entry strip (r8, claude-hrow 2026-10-13).
# Routed evidence (r7 cbe 6_final.def, DRC 21): every marker is an M4 stub that runs from an M5 track
# just inside the east macro edge (x 442.81..443.10, the first tracks past the old 0.30 um guard) out to
# the channel: the router used M5 over the macro as a vertical lane beside the channel and dropped VIA45
# onto M4, which is OBS over the whole macro (0.072 um in from each edge). A 0.30 um guard only moved the
# drop deeper. Contract now: M5 over an SRAM is N-S pass-through only. A CX_STRIP-wide M5 strip inside each
# vertical macro edge has no M5 at all (global and detailed route), so no guide changes layer there; the
# edge pins (M4, 0.024 um wide) are reached planar on M4 from the channel and VIA45 lands outside the macro.
set cx_strip_um [expr {[info exists ::env(OT_CX_HROW_STRIP_UM)] ? $::env(OT_CX_HROW_STRIP_UM) : 6.0}]
set cx_caller [dict get [info frame -1] file]
set cx_stage [file tail $cx_caller]
puts "CX_HROW SRAM hook invoked caller=$cx_stage"
if {[string match *pre_grt.tcl $cx_stage] || [string match *post_drt.tcl $cx_stage]} {
  set b [ord::get_db_block]
  set t [[ord::get_db] getTech]
  set u [$b getDbUnitsPerMicron]
  set rects {}
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_1024x256_m2_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMax]-round($cx_strip_um*$u)}] [$r yMin] [expr {[$r xMax]-round(0.024*$u)}] [$r yMax]]
  }
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_1024x256_m2_r2c2"} continue
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMin]+round(0.024*$u)}] [$r yMin] [expr {[$r xMin]+round($cx_strip_um*$u)}] [$r yMax]]
  }
  set count 0
  if {[string match *pre_grt.tcl $cx_stage]} {
    foreach r $rects { odb::dbObstruction_create $b [$t findLayer M5] {*}$r; incr count }
    if {$count != 8} { error "CX_HROW expected 8 guards, created $count" }
    puts "CX_HROW SRAM access keepout created $count strip $cx_strip_um um"
  } else {
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M5"} continue
      set k [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {[lsearch -exact $rects $k] >= 0} { odb::dbObstruction_destroy $o; incr count }
    }
    if {$count != 8} { error "CX_HROW expected 8 guards, removed $count" }
    puts "CX_HROW SRAM access keepout removed $count"
  }
}
