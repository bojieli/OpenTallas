# POST_RESIZE hook (spec orfs_vars POST_RESIZE_TCL=physical/common_flow/post_resize_relocate.tcl): re-place the
# repair_design buffers that 3_4 dropped onto hard macros / hard placement blockages, BEFORE detailed placement.
# Root cause (Q-COMPUTE-ELEM r13, 2026-10-15, qfd_tile_nk_banked_v1 bp58b): 3_4 repair_design inserted 86,153 wire
# buffers in 30,763 long nets of a wire-dominated 83-macro parent (instances 111,137 -> 197,290); rsz puts them on the
# Steiner points, so 40,866 movable cells sat INSIDE hard-macro footprints (GPL had left 2.9k) -- tens of um from any
# legal row, beyond DPL's displacement window -> the negotiation legaliser stalled and DPL crashed.  Fix: every
# movable CORE cell whose centre is inside a block instance or a hard placement blockage is unplaced, then ONE
# incremental global placement puts those cells (and spreads the rest) into legal free area by wirelength + density;
# FIRM pin flops / hold stages stay fixed.  Wire / slew effects are measured downstream (CTS repair + STA): no
# timing is waived here.  Measured on the bp58b ODB: 40,729 + 15,298 cells unplaced -> 3,052 / 1,540 after GPL.
set ot_rb [ord::get_db_block]
set ot_rr {}
foreach ot_i [$ot_rb getInsts] {
  if {[[$ot_i getMaster] isBlock]} { set ot_bb [$ot_i getBBox]; lappend ot_rr [list [$ot_bb xMin] [$ot_bb yMin] [$ot_bb xMax] [$ot_bb yMax]] }
}
foreach ot_k [$ot_rb getBlockages] {
  if {[$ot_k isSoft] || [$ot_k getMaxDensity] > 0} continue
  set ot_bb [$ot_k getBBox]; lappend ot_rr [list [$ot_bb xMin] [$ot_bb yMin] [$ot_bb xMax] [$ot_bb yMax]]
}
set ot_un 0
foreach ot_i [$ot_rb getInsts] {
  if {[[$ot_i getMaster] isBlock] || [$ot_i isFixed] || [[$ot_i getMaster] getType] ne "CORE"} continue
  set ot_bb [$ot_i getBBox]
  set ot_x [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}]; set ot_y [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]
  foreach ot_m $ot_rr {
    lassign $ot_m a c e f
    if {$ot_x >= $a && $ot_x < $e && $ot_y >= $c && $ot_y < $f} { $ot_i setPlacementStatus NONE; incr ot_un; break }
  }
}
puts "OT_RELOCATE unplaced $ot_un movable cells inside hard macros / hard blockages"
if {$ot_un > 0} {
  set ot_pd 0.5
  if {[info exists ::env(PLACE_DENSITY)] && $::env(PLACE_DENSITY) ne ""} { set ot_pd $::env(PLACE_DENSITY) }
  global_placement -incremental -density $ot_pd
  estimate_parasitics -placement
}
