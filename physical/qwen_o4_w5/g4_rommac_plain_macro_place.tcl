# Written by tools/qwen_o4_floorplan.py: ROM/MAC neighbourhood macro placement (um)
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

ot_place {g_pair[0].g_bank[0].u_rom} 61.344 2.16 R0
ot_place {g_pair[0].g_bank[1].u_rom} 61.344 71.28 R0
ot_place {g_pair[0].g_bank[2].u_rom} 61.344 140.4 R0
ot_place {g_pair[0].g_bank[3].u_rom} 61.344 209.52 R0
ot_place {g_pair[0].g_bank[4].u_rom} 61.344 278.64 R0
ot_place {g_pair[0].g_bank[5].u_rom} 61.344 347.76 R0
ot_place {g_pair[0].g_bank[6].u_rom} 305.424 2.16 R0
ot_place {g_pair[0].g_bank[7].u_rom} 305.424 71.28 R0
ot_place {g_pair[0].g_bank[8].u_rom} 305.424 140.4 R0
ot_place {g_pair[0].g_bank[9].u_rom} 305.424 209.52 R0
ot_place {g_pair[0].g_bank[10].u_rom} 305.424 278.64 R0
ot_place {g_pair[1].g_bank[0].u_rom} 549.504 2.16 R0
ot_place {g_pair[1].g_bank[1].u_rom} 549.504 71.28 R0
ot_place {g_pair[1].g_bank[2].u_rom} 549.504 140.4 R0
ot_place {g_pair[1].g_bank[3].u_rom} 549.504 209.52 R0
ot_place {g_pair[1].g_bank[4].u_rom} 549.504 278.64 R0
ot_place {g_pair[1].g_bank[5].u_rom} 549.504 347.76 R0
ot_place {g_pair[1].g_bank[6].u_rom} 793.584 2.16 R0
ot_place {g_pair[1].g_bank[7].u_rom} 793.584 71.28 R0
ot_place {g_pair[1].g_bank[8].u_rom} 793.584 140.4 R0
ot_place {g_pair[1].g_bank[9].u_rom} 793.584 209.52 R0
ot_place {g_pair[1].g_bank[10].u_rom} 793.584 278.64 R0
puts "ot_place: 22 macros placed"
