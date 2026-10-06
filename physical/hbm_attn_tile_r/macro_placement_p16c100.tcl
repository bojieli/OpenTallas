# H16 parent of four quads (tools/hbm_attn_quad_parent_place.py): quad 514.89 x 562.95 um, channel 100.0 um,
# row gap 20.0 um; quad pin phases M4 y 12 / M5 x 12 nm; die 1149.822 x 1166.13 um
place_macro -macro_name {g_y\[0\].g_x\[0\].u_q} -location {10.014 10.032} -orientation MY -exact
place_macro -macro_name {g_y\[0\].g_x\[1\].u_q} -location {624.912 10.032} -orientation R0 -exact
place_macro -macro_name {g_y\[1\].g_x\[0\].u_q} -location {10.014 592.992} -orientation MY -exact
place_macro -macro_name {g_y\[1\].g_x\[1\].u_q} -location {624.912 592.992} -orientation R0 -exact
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  if {[[$ot_i getMaster] getName] ne "ot_attn_tile_m6h1q"} {continue}
  $ot_i setPlacementStatus FIRM
  foreach ot_t [$ot_i getITerms] {
    set ot_m [[$ot_t getMTerm] getName]
    if {$ot_m ne "ib\[0\]" && $ot_m ne "clk" && $ot_m ne "oy\[0\]" && $ot_m ne "oy\[127\]"} {continue}
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
if {$ot_n != 4} {error "expected 4 quads, placed $ot_n"}
puts OT_P16_QUADS_PLACED_ON_GRID
