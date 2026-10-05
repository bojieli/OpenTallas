# Slab port-group element macro placement (um): 16 ot_rom_4096x266_m8 scale banks, 4 columns x (2 rows south +
# 2 rows north) around a 73 um logic band.  R0 only (mirrored macros put pins off the M4 tracks); y on the 2.16 um
# lattice (0.27 um rows x 0.048 um M4 pitch); columns leave 35.6 um edge channels and 71.5 um inner channels for the
# pin-side capture flops (pins on both vertical edges, lowest 14 um).
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
ot_place {g_col[0].g_bank[0].u_rom} 37.8 2.16 R0
ot_place {g_col[0].g_bank[1].u_rom} 37.8 71.28 R0
ot_place {g_col[0].g_bank[2].u_rom} 37.8 207.36 R0
ot_place {g_col[0].g_bank[3].u_rom} 37.8 276.48 R0
ot_place {g_col[1].g_bank[0].u_rom} 231.12 2.16 R0
ot_place {g_col[1].g_bank[1].u_rom} 231.12 71.28 R0
ot_place {g_col[1].g_bank[2].u_rom} 231.12 207.36 R0
ot_place {g_col[1].g_bank[3].u_rom} 231.12 276.48 R0
ot_place {g_col[2].g_bank[0].u_rom} 424.44 2.16 R0
ot_place {g_col[2].g_bank[1].u_rom} 424.44 71.28 R0
ot_place {g_col[2].g_bank[2].u_rom} 424.44 207.36 R0
ot_place {g_col[2].g_bank[3].u_rom} 424.44 276.48 R0
ot_place {g_col[3].g_bank[0].u_rom} 617.76 2.16 R0
ot_place {g_col[3].g_bank[1].u_rom} 617.76 71.28 R0
ot_place {g_col[3].g_bank[2].u_rom} 617.76 207.36 R0
ot_place {g_col[3].g_bank[3].u_rom} 617.76 276.48 R0
