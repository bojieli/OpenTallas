# CLAUDE S81-PH dsfd_selt_q2 (SAFE selector quarter): the six ot_sram_1r1w_128x256_m1_r2c2 line-memory macros
# u_q.g_m2.u_mem.g_b[b].g_w[w].u_m in one row along the S edge, R0, slot k = 3 b + w at x = 21.6 + k * 101.52, y = 5.4.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_b\\?\[(\d)\\?\]\.g_w\\?\[(\d)\\?\]\.u_m$} $ot_nm -> ot_b ot_w]} { continue }
  set ot_k [expr {3 * $ot_b + $ot_w}]
  place_macro -macro_name $ot_nm -location [list [expr {21.6 + $ot_k * 101.52}] 5.4] -orientation R0
  incr ot_n
}
if {$ot_n != 6} { error "place_macros_q2: placed $ot_n macros, expected 6" }
puts "place_macros_q2: $ot_n macros placed"
