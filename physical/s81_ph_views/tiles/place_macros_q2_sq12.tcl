# CLAUDE safe-s81 2026-10-08 (review S-B2 + coordinator: fp-lint sliver rule, layout only, 0 cycles): dsfd_selt_q2
# square variant (432 x 280.8, contract_selsq) as place_macros_q2_sq.tcl, but the two macro rows are 54.0 um apart
# (was 48.6: a 7.5 um sliver between the 41.064-um-tall macros) -> 12.9 um gap >= the 12 um sliver limit.
# Columns stay 118.8 apart (24.0 um gaps).  slot k = 3 b + w: x = 21.6 + (k % 3) * 118.8, y = 5.4 + (k / 3) * 54.0, R0.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_b\\?\[(\d)\\?\]\.g_w\\?\[(\d)\\?\]\.u_m$} $ot_nm -> ot_b ot_w]} { continue }
  set ot_k [expr {3 * $ot_b + $ot_w}]
  place_macro -macro_name $ot_nm -location [list [expr {21.6 + ($ot_k % 3) * 118.8}] [expr {5.4 + ($ot_k / 3) * 54.0}]] -orientation R0
  incr ot_n
}
if {$ot_n != 6} { error "place_macros_q2_sq12: placed $ot_n macros, expected 6" }
puts "place_macros_q2_sq12: $ot_n macros placed"
