# H16 registered tile ot_attn_tile_m6h1r, floorplan f4c100: macro pairs facing a 100 um register channel, a 60 um
# centre gap and a 60 um middle strip between rows 1 and 2 (the ROOT -> centre chain -> COL distribution), 20 um row gaps,
# 20 um side and 20 / 20 um bottom / top margins; origins on the M4/M5 pin grids (see macro_placement_c70.tcl).
# die 1479.222 x 1319.22 um
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[0\].g_s\[0\].u_g} -location {20.026 20.016} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[0\].g_s\[1\].u_g} -location {414.816 20.016} -orientation R0 -exact
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[1\].g_s\[0\].u_g} -location {20.026 334.800} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[1\].g_s\[1\].u_g} -location {414.816 334.800} -orientation R0 -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[0\].g_s\[0\].u_g} -location {20.026 689.616} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[0\].g_s\[1\].u_g} -location {414.816 689.616} -orientation R0 -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[1\].g_s\[0\].u_g} -location {20.026 1004.400} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[1\].g_s\[1\].u_g} -location {414.816 1004.400} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[0\].g_s\[0\].u_g} -location {769.642 20.016} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[0\].g_s\[1\].u_g} -location {1164.432 20.016} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[1\].g_s\[0\].u_g} -location {769.642 334.800} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[1\].g_s\[1\].u_g} -location {1164.432 334.800} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[0\].g_s\[0\].u_g} -location {769.642 689.616} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[0\].g_s\[1\].u_g} -location {1164.432 689.616} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[1\].g_s\[0\].u_g} -location {769.642 1004.400} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[1\].g_s\[1\].u_g} -location {1164.432 1004.400} -orientation R0 -exact
set ot_b [ord::get_db_block]
set ot_n 0
foreach ot_i [$ot_b getInsts] {
  if {[[$ot_i getMaster] getName] ne "ot_attn_hgrp_m6h1"} {continue}
  $ot_i setPlacementStatus FIRM
  foreach ot_t [$ot_i getITerms] {
    set ot_m [[$ot_t getMTerm] getName]
    if {$ot_m ne "ib\[288\]" && $ot_m ne "iv" && $ot_m ne "ld_w\[0\]" && $ot_m ne "rst_n"} {continue}
    set ot_bb [$ot_t getBBox]
    set ot_xc [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}]
    set ot_yc [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]
    set ot_l [[[lindex [[lindex [[$ot_t getMTerm] getMPins] 0] getGeometry] 0] getTechLayer] getName]
    if {$ot_l eq "M4"} {set ot_ph [expr {$ot_yc % 48}]} else {set ot_ph [expr {$ot_xc % 48}]}
    puts "OT_PINPHASE [$ot_i getName] [$ot_i getOrient] $ot_m $ot_l centre=$ot_xc,$ot_yc phase=$ot_ph"
    if {$ot_ph != 12} {error "pin $ot_m of [$ot_i getName] off the $ot_l track grid (phase $ot_ph)"}
  }
  incr ot_n
}
if {$ot_n != 16} {error "expected 16 leaves, placed $ot_n"}
puts OT_H16R_MACROS_PLACED_ON_GRID
