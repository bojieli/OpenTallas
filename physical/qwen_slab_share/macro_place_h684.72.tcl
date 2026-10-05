# tools/qwen_slab_share.py: slab port-group share 777.576 x 684.720 um; 16 scale banks R0 (4 columns x 4 rows)
# and the b3r16B40 entry strip: M6/M7 obstructed over x 0..40 um (the bw_ / array-facing face).
set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} {
    dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName]
  }
}
proc ot_place {name x y orient} {
  global ot_lut
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient
}
ot_place {g_col[0].g_bank[0].u_rom} 37.8 64.8 R0
ot_place {g_col[0].g_bank[1].u_rom} 37.8 192.24 R0
ot_place {g_col[0].g_bank[2].u_rom} 37.8 427.68 R0
ot_place {g_col[0].g_bank[3].u_rom} 37.8 555.12 R0
ot_place {g_col[1].g_bank[0].u_rom} 231.12 64.8 R0
ot_place {g_col[1].g_bank[1].u_rom} 231.12 192.24 R0
ot_place {g_col[1].g_bank[2].u_rom} 231.12 427.68 R0
ot_place {g_col[1].g_bank[3].u_rom} 231.12 555.12 R0
ot_place {g_col[2].g_bank[0].u_rom} 424.44 64.8 R0
ot_place {g_col[2].g_bank[1].u_rom} 424.44 192.24 R0
ot_place {g_col[2].g_bank[2].u_rom} 424.44 427.68 R0
ot_place {g_col[2].g_bank[3].u_rom} 424.44 555.12 R0
ot_place {g_col[3].g_bank[0].u_rom} 617.76 64.8 R0
ot_place {g_col[3].g_bank[1].u_rom} 617.76 192.24 R0
ot_place {g_col[3].g_bank[2].u_rom} 617.76 427.68 R0
ot_place {g_col[3].g_bank[3].u_rom} 617.76 555.12 R0
set ot_tech [ord::get_db_tech]
set ot_dbu [$ot_tech getDbUnitsPerMicron]
foreach ot_l {M6 M7} {
  odb::dbObstruction_create $ot_block [$ot_tech findLayer $ot_l] 0 0 [expr {round(40.0 * $ot_dbu)}] [expr {round(684.72 * $ot_dbu)}]
}
