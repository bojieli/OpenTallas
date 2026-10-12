# el1011-q-kvd 2026-10-11: KV-end (qkd_d2d_s / _t) macro plan.  The four ot_sram_1r1w_64x512 link-buffer bodies sit as a
# 2 x 2 block in the centre of the core with 40 um channels between them, far from the pin-dense S (t_* / r_*) and N
# (tx/rx flit) faces, so no macro shadows a pin edge and every edge keeps a full standard-cell band.  R0 only (mirrored
# macros put pins off track).  Positions snap to 1.08 um (row 0.27 / site 0.054).
set sb_block [ord::get_db_block]
set sb_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set sb_macros {}
foreach m [$sb_block getInsts] {
  if {[[$m getMaster] isBlock] && [[$m getMaster] getName] eq "ot_sram_1r1w_64x512_m1_r2c2"} { lappend sb_macros [$m getName] }
}
if {[llength $sb_macros] != 4} { error "qkd_d2d_sb_place: expected 4 ot_sram_1r1w_64x512 macros, found [llength $sb_macros]" }
set core [$sb_block getCoreArea]
set cx0 [expr {[$core xMin] / double($sb_dbu)}]; set cy0 [expr {[$core yMin] / double($sb_dbu)}]
set cx1 [expr {[$core xMax] / double($sb_dbu)}]; set cy1 [expr {[$core yMax] / double($sb_dbu)}]
set mw 171.288; set mh 77.784; set ch 40.0
set x0 [expr {1.08 * round((($cx0 + $cx1) / 2.0 - $mw - $ch / 2.0) / 1.08)}]
set y0 [expr {1.08 * round((($cy0 + $cy1) / 2.0 - $mh - $ch / 2.0) / 1.08)}]
set i 0
foreach name [lsort -dictionary $sb_macros] {
  set m [$sb_block findInst $name]
  set x [expr {$x0 + ($i % 2) * 1.08 * ceil(($mw + $ch) / 1.08)}]
  set y [expr {$y0 + ($i / 2) * 1.08 * ceil(($mh + $ch) / 1.08)}]
  $m setOrient R0
  $m setLocation [expr {round($x * $sb_dbu)}] [expr {round($y * $sb_dbu)}]
  $m setPlacementStatus FIRM
  puts "qkd_d2d_sb_place: $name at $x $y"
  incr i
}
