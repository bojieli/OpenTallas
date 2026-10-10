# redesign-qwen 2026-10-09: qfd_su_cbuf_g -- the group SRAM centred, 30 um below the N (far-ROM fill) pin face, the
# SU-side answer pipeline between it and the S (crom_*) face.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_die [$ot_blk getDieArea]
set W [expr {double([$ot_die xMax] - [$ot_die xMin]) / $ot_dbu}]
set H [expr {double([$ot_die yMax] - [$ot_die yMin]) / $ot_dbu}]
set MW 174.744
set MH 70.47
set x [expr {round((($W - $MW) / 2.0) / 0.054) * 0.054}]
set y [expr {round(($H - $MH - 30.0) / 0.27) * 0.27}]
foreach ot_inst [$ot_blk getInsts] {
  if {[[$ot_inst getMaster] isBlock]} { place_macro -macro_name [$ot_inst getName] -location [list $x $y] -orientation R0 }
}
