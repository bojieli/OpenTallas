# hfd_attn_tile die view (CLAUDE HBM-ABSTRACTS attn): four ot_attn_tile_m6h1q quads in the r16g tile outline
# 1349.112 x 1349.976 um, input (left) edges facing a 180.6 um central channel (left quads MY), side channels
# 70.0 / 68.7 um, bottom 40.0 / middle 160.65 / top 23.4 um.  Positions keep the quads' pin phases (M4 y / M5 x 12 nm
# mod 48) AND put every quad M9 PG stripe and M8 PG stub on the parent's 5.4 um PG lattice (R0 - MY x offset
# 695.49 = 4.29 mod 10.8; row pitch 723.6 = 67 x 10.8), so the parent's M8 / M9 straps meet the quads' PG pins.
place_macro -macro_name {g_y\[0\].g_x\[0\].u_q} -location {70.014 40.032} -orientation MY -exact
place_macro -macro_name {g_y\[0\].g_x\[1\].u_q} -location {765.504 40.032} -orientation R0 -exact
place_macro -macro_name {g_y\[1\].g_x\[0\].u_q} -location {70.014 763.632} -orientation MY -exact
place_macro -macro_name {g_y\[1\].g_x\[1\].u_q} -location {765.504 763.632} -orientation R0 -exact
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
puts OT_HFD_ATTN_QUADS_PLACED_ON_GRID
