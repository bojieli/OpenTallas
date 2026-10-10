# redesign-qwen 2026-10-09: qfd_su_cbuf macro placement -- the 8 group SRAMs (u_b.g_sram.g_grp[g].u_m) in one row at mid
# height, macro g centred over its 8 lanes' span of the S (crom_*) and N (f_*) pin faces (lane-major pin order), so every
# lane group's pins, logic and SRAM sit in one vertical slice; channels above and below the row to both pin faces.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_die [$ot_blk getDieArea]
set W [expr {double([$ot_die xMax] - [$ot_die xMin]) / $ot_dbu}]
set H [expr {double([$ot_die yMax] - [$ot_die yMin]) / $ot_dbu}]
set MW 174.744
set MH 70.47
set slot [expr {$W / 8.0}]
set y [expr {round((($H - $MH) / 2.0) / 0.27) * 0.27}]
set ot_lut [dict create]
foreach ot_inst [$ot_blk getInsts] {
  if {[[$ot_inst getMaster] isBlock]} { dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName] }
}
for {set g 0} {$g < 8} {incr g} {
  set x [expr {round(($g * $slot + ($slot - $MW) / 2.0) / 0.054) * 0.054}]
  set nm "u_b.g_sram.g_grp\[$g\].u_m"
  if {![dict exists $ot_lut $nm]} { error "su_cbuf_place: no macro $nm" }
  place_macro -macro_name [dict get $ot_lut $nm] -location [list $x $y] -orientation R0
}
