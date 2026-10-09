# gaps-design 2026-10-08: qfd_io_serdes adapter, RXD = 512 receive buffer = 8 x ot_sram_1r1w_512x128_m4_r2c2 (128-bit
# slices of the 1,024-bit word) as 2 columns x 4 rows in the die centre between the FDI (bottom) and die-RX (right) faces;
# 9.9 um / 10.7 um stdcell channels, all R0, origins on the 0.048-um macro grid.
set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} { dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName] }
}
proc ot_place {name x y} {
  global ot_lut
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name (have [dict keys $ot_lut])" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation R0
}
ot_place {u_rb.g_sram.g_t[0].u_m} 200.016 199.968
ot_place {u_rb.g_sram.g_t[1].u_m} 200.016 240.384
ot_place {u_rb.g_sram.g_t[2].u_m} 200.016 280.800
ot_place {u_rb.g_sram.g_t[3].u_m} 200.016 321.216
ot_place {u_rb.g_sram.g_t[4].u_m} 384.048 199.968
ot_place {u_rb.g_sram.g_t[5].u_m} 384.048 240.384
ot_place {u_rb.g_sram.g_t[6].u_m} 384.048 280.800
ot_place {u_rb.g_sram.g_t[7].u_m} 384.048 321.216
