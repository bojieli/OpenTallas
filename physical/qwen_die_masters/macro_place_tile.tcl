# tools-free macro placement of the die tile frame (qfd_tile 266.952 x 1291.656): ROM banks b0-b2 at the south end,
# b3-b4 at the north end, KV slice SRAMs under the north banks; logic band in between (tap / tree pins at mid-height).
set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} { dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName] }
}
proc ot_place {name x y orient} {
  global ot_lut
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient
}
ot_place {g_col[0].g_bank[0].u_rom} 2.16 2.16 R0
ot_place {g_col[1].g_bank[0].u_rom} 142.992 2.16 R0
ot_place {g_col[0].g_bank[1].u_rom} 2.16 69.552 R0
ot_place {g_col[1].g_bank[1].u_rom} 142.992 69.552 R0
ot_place {g_col[0].g_bank[2].u_rom} 2.16 136.944 R0
ot_place {g_col[1].g_bank[2].u_rom} 142.992 136.944 R0
ot_place {g_col[0].g_bank[3].u_rom} 2.16 1226.448 R0
ot_place {g_col[1].g_bank[3].u_rom} 142.992 1226.448 R0
ot_place {g_col[0].g_bank[4].u_rom} 2.16 1158.840 R0
ot_place {g_col[1].g_bank[4].u_rom} 142.992 1158.840 R0
ot_place {g_kv[0].u_kv} 2.16 1113.264 R0
ot_place {g_kv[1].u_kv} 169.992 1113.264 R0
