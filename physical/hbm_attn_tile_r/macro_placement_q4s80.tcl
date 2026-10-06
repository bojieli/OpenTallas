# H16 registered tile, two-strip floorplan (tools/hbm_attn_strip_place.py): leaf 241.4 x 241.4 um,
# strips 80.0 um (rows 0|1 and 2|3), middle gap 40.0 um, column gaps 12.0 um, margins 10.0 um;
# die 514.89 x 582.93 um
place_macro -macro_name {g_r\[0\].g_s\[0\].u_g} -location {10.032 10.032} -orientation R0 -exact
place_macro -macro_name {g_r\[0\].g_s\[1\].u_g} -location {263.472 10.032} -orientation R0 -exact
place_macro -macro_name {g_r\[1\].g_s\[0\].u_g} -location {10.032 331.440} -orientation MX -exact
place_macro -macro_name {g_r\[1\].g_s\[1\].u_g} -location {263.472 331.440} -orientation MX -exact
set ot_b [ord::get_db_block]
set ot_n 0
foreach ot_i [$ot_b getInsts] {
  if {[[$ot_i getMaster] getName] ne "ot_attn_hgrp_m6h1"} {continue}
  $ot_i setPlacementStatus FIRM
  foreach ot_t [$ot_i getITerms] {
    set ot_m [[$ot_t getMTerm] getName]
    if {$ot_m ne "ib\[288\]" && $ot_m ne "iv" && $ot_m ne "ld_w\[0\]" && $ot_m ne "rst_n" && $ot_m ne "clk" && $ot_m ne "oy\[0\]"} {continue}
    set ot_bb [$ot_t getBBox]
    set ot_xc [expr {([$ot_bb xMin] + [$ot_bb xMax]) / 2}]
    set ot_yc [expr {([$ot_bb yMin] + [$ot_bb yMax]) / 2}]
    set ot_l [[[lindex [[lindex [[$ot_t getMTerm] getMPins] 0] getGeometry] 0] getTechLayer] getName]
    if {$ot_l eq "M4" || $ot_l eq "M6"} {set ot_ph [expr {$ot_yc % 48}]} else {set ot_ph [expr {$ot_xc % 48}]}
    puts "OT_PINPHASE [$ot_i getName] [$ot_i getOrient] $ot_m $ot_l centre=$ot_xc,$ot_yc phase=$ot_ph"
    if {$ot_ph != 12} {error "pin $ot_m of [$ot_i getName] off the $ot_l track grid (phase $ot_ph)"}
  }
  incr ot_n
}
if {$ot_n != 4} {error "expected 4 leaves, placed $ot_n"}
puts OT_H16S_MACROS_PLACED_ON_GRID
