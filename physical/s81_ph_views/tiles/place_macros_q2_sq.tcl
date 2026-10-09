# CLAUDE s81-blocks: dsfd_selt_q2 square variant (432 x 280.8, contract_selsq): the six 128x256 line-memory macros in
# two rows of three along the S edge, slot k = 3 b + w: x = 21.6 + (k % 3) * 118.8, y = 5.4 + (k / 3) * 48.6, R0.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_b\\?\[(\d)\\?\]\.g_w\\?\[(\d)\\?\]\.u_m$} $ot_nm -> ot_b ot_w]} { continue }
  set ot_k [expr {3 * $ot_b + $ot_w}]
  place_macro -macro_name $ot_nm -location [list [expr {21.6 + ($ot_k % 3) * 118.8}] [expr {5.4 + ($ot_k / 3) * 48.6}]] -orientation R0
  incr ot_n
}
if {$ot_n != 6} { error "place_macros_q2_sq: placed $ot_n macros, expected 6" }
puts "place_macros_q2_sq: $ot_n macros placed"
