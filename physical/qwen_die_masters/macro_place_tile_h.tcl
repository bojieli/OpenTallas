# qwen-blocks: half-depth bank layout (BAW 11, CODE_BANKS 10: ot_rom_2048x266_m8 121.392 x 34.56): banks 0-4 south,
# 5-9 north (the ROM_PIPE groups), KV slice SRAMs under the north banks.
# tools-free macro placement of the die tile frame (qfd_tile 266.952 x 1291.656): ROM banks b0-b2 at the south end,
# b3-b4 at the north end, KV slice SRAMs under the north banks; logic band in between (tap / tree pins at mid-height).
set ot_block [ord::get_db_block]
set ot_lut [dict create]
foreach ot_inst [$ot_block getInsts] {
  if {[[$ot_inst getMaster] isBlock]} { dict set ot_lut [string map {"\\" ""} [$ot_inst getName]] [$ot_inst getName] }
}
# QDM_MACRO_PREFIX: hierarchy prefix when the tile sits inside a wrapper (qfd_tile = ot_qwen_rom_tile_die: "u_tile.")
set ot_pfx [expr {[info exists ::env(QDM_MACRO_PREFIX)] ? $::env(QDM_MACRO_PREFIX) : ""}]
proc ot_place {name x y orient} {
  global ot_lut ot_pfx
  set name "$ot_pfx$name"
  if {![dict exists $ot_lut $name]} { error "ot_place: no macro instance $name" }
  place_macro -macro_name [dict get $ot_lut $name] -location [list $x $y] -orientation $orient
}
ot_place {g_col[0].g_bank[0].g_h.u_rom} 2.16 2.16 R0
ot_place {g_col[0].g_bank[1].g_h.u_rom} 2.16 41.04 R0
ot_place {g_col[0].g_bank[2].g_h.u_rom} 2.16 79.92 R0
ot_place {g_col[0].g_bank[3].g_h.u_rom} 2.16 118.8 R0
ot_place {g_col[0].g_bank[4].g_h.u_rom} 2.16 157.68 R0
ot_place {g_col[0].g_bank[5].g_h.u_rom} 2.16 1254.528 R0
ot_place {g_col[0].g_bank[6].g_h.u_rom} 2.16 1215.648 R0
ot_place {g_col[0].g_bank[7].g_h.u_rom} 2.16 1176.768 R0
ot_place {g_col[0].g_bank[8].g_h.u_rom} 2.16 1137.888 R0
ot_place {g_col[0].g_bank[9].g_h.u_rom} 2.16 1099.008 R0
ot_place {g_col[1].g_bank[0].g_h.u_rom} 142.776 2.16 R0
ot_place {g_col[1].g_bank[1].g_h.u_rom} 142.776 41.04 R0
ot_place {g_col[1].g_bank[2].g_h.u_rom} 142.776 79.92 R0
ot_place {g_col[1].g_bank[3].g_h.u_rom} 142.776 118.8 R0
ot_place {g_col[1].g_bank[4].g_h.u_rom} 142.776 157.68 R0
ot_place {g_col[1].g_bank[5].g_h.u_rom} 142.776 1254.528 R0
ot_place {g_col[1].g_bank[6].g_h.u_rom} 142.776 1215.648 R0
ot_place {g_col[1].g_bank[7].g_h.u_rom} 142.776 1176.768 R0
ot_place {g_col[1].g_bank[8].g_h.u_rom} 142.776 1137.888 R0
ot_place {g_col[1].g_bank[9].g_h.u_rom} 142.776 1099.008 R0
ot_place {g_kv[0].u_kv} 2.16 1053.648 R0
ot_place {g_kv[1].u_kv} 169.884 1053.648 R0
