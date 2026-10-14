# SRAM vertical-edge M5 no-entry strip for the VM8 slice tiles (FACE3 2026-10-13); the hrow5 r8 / dscoll cxea3 hook
# (physical/dscoll_cx/sram_edge_strip.tcl, routed DRC 0 there) for ot_sram_1r1w_128x256_m1_r2c2, any macro count.
# Contract: M5 over an SRAM is N-S pass-through only; a strip-wide band inside each vertical macro edge has no M5, the
# M4 edge pins are reached planar from the channel and VIA45 lands outside the macro.  Evidence for this tile
# (vm_cp_slice3_cx-cx1-2c31a0533 congestion-30.rpt): 3,549 horizontal markers at capacity 0, all x 90-160 = up to 20 um
# INSIDE the two macro columns' centre-facing edges (wires leaving M5 over the macro for the edge pins).
# Created pre-GRT, removed post-DRT (the abstract carries real metal only).
set vm_strip_um [expr {[info exists ::env(OT_VM_SRAM_STRIP_UM)] ? $::env(OT_VM_SRAM_STRIP_UM) : 6.0}]
set vm_stage [file tail [dict get [info frame -1] file]]
puts "VM_SRAM_STRIP hook invoked caller=$vm_stage"
if {[string match *pre_grt.tcl $vm_stage] || [string match *post_drt.tcl $vm_stage]} {
  set b [ord::get_db_block]
  set t [[ord::get_db] getTech]
  set u [$b getDbUnitsPerMicron]
  set rects {}
  set nm 0
  foreach i [$b getInsts] {
    if {[[$i getMaster] getName] ne "ot_sram_1r1w_128x256_m1_r2c2"} continue
    incr nm
    set r [$i getBBox]
    lappend rects [list [expr {[$r xMax]-round($vm_strip_um*$u)}] [$r yMin] [expr {[$r xMax]-round(0.024*$u)}] [$r yMax]]
    lappend rects [list [expr {[$r xMin]+round(0.024*$u)}] [$r yMin] [expr {[$r xMin]+round($vm_strip_um*$u)}] [$r yMax]]
  }
  if {$nm == 0} { error "VM_SRAM_STRIP: no ot_sram_1r1w_128x256_m1_r2c2 instance" }
  set count 0
  if {[string match *pre_grt.tcl $vm_stage]} {
    foreach r $rects { odb::dbObstruction_create $b [$t findLayer M5] {*}$r; incr count }
    puts "VM_SRAM_STRIP created $count M5 strips ($vm_strip_um um) on $nm macros"
  } else {
    foreach o [$b getObstructions] {
      set r [$o getBBox]
      if {[[$r getTechLayer] getName] ne "M5"} continue
      set k [list [$r xMin] [$r yMin] [$r xMax] [$r yMax]]
      if {[lsearch -exact $rects $k] >= 0} { odb::dbObstruction_destroy $o; incr count }
    }
    if {$count != 2*$nm} { error "VM_SRAM_STRIP expected [expr {2*$nm}] strips, removed $count" }
    puts "VM_SRAM_STRIP removed $count"
  }
}
