# redesign-qwen 2026-10-09: qfd_crom_g -- the 6 ROM macros (narrow column 0 x 2 deep, wide columns 0 / 1 x 2 deep) in one
# column on the E side, 50 um above the S (lane) pin face; the lanes' decode / capture / output logic in the W channel.
set ot_blk [ord::get_db_block]
set ot_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set ot_die [$ot_blk getDieArea]
set W [expr {double([$ot_die xMax] - [$ot_die xMin]) / $ot_dbu}]
set MW 121.824
set MH 62.910
set ot_lut [dict create]
foreach ot_inst [$ot_blk getInsts] {
  if {[[$ot_inst getMaster] isBlock]} { dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName] }
}
set order {u_c.g_n[0].g_d[0].u_m u_c.g_n[0].g_d[1].u_m u_c.g_w[0].g_d[0].u_m u_c.g_w[0].g_d[1].u_m u_c.g_w[1].g_d[0].u_m u_c.g_w[1].g_d[1].u_m}
set x [expr {round(($W - $MW - 10.8) / 0.054) * 0.054}]
set i 0
foreach nm $order {
  if {![dict exists $ot_lut $nm]} { error "crom_g_place: no macro $nm" }
  set y [expr {round((48.0 + $i * ($MH + 13.5)) / 0.27) * 0.27}]
  place_macro -macro_name [dict get $ot_lut $nm] -location [list $x $y] -orientation R0
  incr i
}
