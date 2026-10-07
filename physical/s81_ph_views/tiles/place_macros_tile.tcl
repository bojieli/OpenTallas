# CLAUDE S81-PH tiles (redesign pass 2026-10-06): the 256x256 SRAM macros of a tile (dsfd_selt_q: 3 line-memory
# macros u_mem.g_m[i].u_m; dsfd_colt_lane: 2 frame-FIFO macros u_q.g_tile[i].g_m1.u_m) in one row along the S edge,
# R0, x = 21.6 + i * 183.6, y = 5.4 (0.216-um grid), so the W / E face pins sit above the macro band and the E end of
# the quarter tile stays free for the control-tile pins.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_(?:m|tile)\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_k]} { continue }
  place_macro -macro_name $ot_nm -location [list [expr {21.6 + $ot_k * 183.6}] 5.4] -orientation R0
  incr ot_n
}
if {$ot_n < 2} { error "place_macros_tile: placed $ot_n macros" }
puts "place_macros_tile: $ot_n macros placed"
