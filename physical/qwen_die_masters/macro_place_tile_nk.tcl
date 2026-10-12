# el1011-q-tile h3 NK (2026-10-11): qfd_tile_nk 288.36 x 1291.656, no KV slice: ROM col 1 x 164.376, leaves x 27.108 (R0) / 161.19 (MY) (34.3 um spine, 27 um edge strips); every x keeps its h2 value mod 0.432.
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
# el1011-q-tile 2026-10-11 round 2 (qfd_tile_h2 / qfd_tile_e_h2): ROM bands with 12 um row gaps (ROM pins are on the side
# edges, low y), KV under the north band, 8 hardened lane-slice leaves (ot_qwen_tile_lsl 99.792 x 140.4) 2 cols x 4 rows
# in y 235-887: 23.7 um edge strips for the die pin flops, 20 um spine (pins face it: left column R0, right column MY),
# 30 um row channels; landing corridor y 900-1098 left to the parent (li/lo, merge, control, node).  North band ends at the
# snapped core top 1289.25 (MPL-0034 at 1226.586 + 62.91).
ot_place {g_col[0].g_bank[0].u_rom} 2.16 2.16 R0
ot_place {g_col[1].g_bank[0].u_rom} 164.376 2.16 R0
ot_place {g_col[0].g_bank[1].u_rom} 2.16 77.07 R0
ot_place {g_col[1].g_bank[1].u_rom} 164.376 77.07 R0
ot_place {g_col[0].g_bank[2].u_rom} 2.16 151.98 R0
ot_place {g_col[1].g_bank[2].u_rom} 164.376 151.98 R0
ot_place {g_col[0].g_bank[4].u_rom} 2.16 1151.16 R0
ot_place {g_col[1].g_bank[4].u_rom} 164.376 1151.16 R0
ot_place {g_col[0].g_bank[3].u_rom} 2.16 1226.07 R0
ot_place {g_col[1].g_bank[3].u_rom} 164.376 1226.07 R0
set ot_ly {234.9 405.27 575.64 746.01}
for {set k 0} {$k < 4} {incr k} {
  ot_place "u_logic.u_me.g_hier.g_sl\[$k\].g_hd.u_lh" 27.108 [lindex $ot_ly $k] R0
  ot_place "u_logic.u_me.g_hier.g_sl\[[expr {$k + 4}]\].g_hd.u_lh" 161.19 [lindex $ot_ly $k] MY
}
