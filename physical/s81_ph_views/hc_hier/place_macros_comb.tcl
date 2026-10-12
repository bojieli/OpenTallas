# CLAUDE s81-suhc-hier-1011 2026-10-11: ot_s81_hc_comb (575.992 x 640, contract_hcc) y-slice FIFO macros placed by hand.
# Why: the e0b7d84ba pd40/pd45 routes left the 5 ot_sram_1r1w_64x512_m1_r2c2 macros to the macro placer, which put
# g_tile[4] 5 um from the W face (784 signal pins behind it) and left 10 um slivers between macros (FLOORPLAN_MARGIN).
# All four faces carry pins (W/E y 20-583: the croot seams; S x 40-529: chain bus; N x 40-407: centre pins), so the
# macros sit as one 2-column x 3-row block in the S-centre: >= 105 um from W/E, 60 um from S, >= 21.6 um channels
# between macros (no slivers), origins on the asap7 track lattice (tools/ref_tile on_track: 0 off-track pins), R0.
# slot k: col k%2 (x 105.84 / 298.944), row k/2 (y 60.48 / 162.0 / 263.52).
set ot_xs {105.84 298.944}
set ot_ys {60.48 162.0 263.52}
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_yf\.u_yf\.g_tile\\?\[(\d)\\?\]\.g_m0\.u_m$} $ot_nm -> ot_k]} { continue }
  place_macro -macro_name $ot_nm -location [list [lindex $ot_xs [expr {$ot_k % 2}]] [lindex $ot_ys [expr {$ot_k / 2}]]] -orientation R0
  incr ot_n
}
if {$ot_n != 5} { error "place_macros_comb: placed $ot_n macros, expected 5" }
puts "place_macros_comb: $ot_n macros placed"
