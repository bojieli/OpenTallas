# CLAUDE safe-s81 2026-10-08 (coordinator: fp-lint sliver rule on s81b-selt_q2-pipe2-mm2-9ac26e269-tt-d1956, layout
# only, 0 cycles): dsfd_selt_q2 as place_macros_q2.tcl (one row along the S edge, R0), but the pitch is 107.028 um
# (was 101.52: 6.7 um slivers between the 94.824-um-wide macros) -> 12.2 um gaps >= the 12 um sliver limit.
# slot k = 3 b + w at x = 21.6 + k * 107.028 (last macro ends at 651.6 um), y = 5.4.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_b\\?\[(\d)\\?\]\.g_w\\?\[(\d)\\?\]\.u_m$} $ot_nm -> ot_b ot_w]} { continue }
  set ot_k [expr {3 * $ot_b + $ot_w}]
  place_macro -macro_name $ot_nm -location [list [expr {21.6 + $ot_k * 107.028}] 5.4] -orientation R0
  incr ot_n
}
if {$ot_n != 6} { error "place_macros_q2_g12: placed $ot_n macros, expected 6" }
puts "place_macros_q2_g12: $ot_n macros placed"
