# H16 registered tile ot_attn_tile_m6h1r: 4 x 4 one-head leaves, macro pairs facing a 100 um register channel.
# Columns 0/2 mirrored (MY: input pins on the right edge), 1/3 R0 (input pins on the left edge).
# Origins on the native grids: M4 pin centres (phase 12 nm) on the M4 tracks (12 + 48k) needs y = 0 mod 48 nm;
# M5 pins on M5 tracks (12 + 48k) needs x = 0 mod 48 (R0) and x = 10 mod 48 (MY, W = 294.782 = 14 mod 48).
# die 1439.262 x 1244.43 um
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[0\].g_s\[0\].u_g} -location {15.034 10.032} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[0\].g_s\[1\].u_g} -location {409.824 10.032} -orientation R0 -exact
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[1\].g_s\[0\].u_g} -location {15.034 319.824} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[0\].g_r\[1\].g_s\[1\].u_g} -location {409.824 319.824} -orientation R0 -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[0\].g_s\[0\].u_g} -location {15.034 629.616} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[0\].g_s\[1\].u_g} -location {409.824 629.616} -orientation R0 -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[1\].g_s\[0\].u_g} -location {15.034 939.408} -orientation MY -exact
place_macro -macro_name {g_p\[0\].g_h\[1\].g_r\[1\].g_s\[1\].u_g} -location {409.824 939.408} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[0\].g_s\[0\].u_g} -location {734.650 10.032} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[0\].g_s\[1\].u_g} -location {1129.440 10.032} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[1\].g_s\[0\].u_g} -location {734.650 319.824} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[0\].g_r\[1\].g_s\[1\].u_g} -location {1129.440 319.824} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[0\].g_s\[0\].u_g} -location {734.650 629.616} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[0\].g_s\[1\].u_g} -location {1129.440 629.616} -orientation R0 -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[1\].g_s\[0\].u_g} -location {734.650 939.408} -orientation MY -exact
place_macro -macro_name {g_p\[1\].g_h\[1\].g_r\[1\].g_s\[1\].u_g} -location {1129.440 939.408} -orientation R0 -exact
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
