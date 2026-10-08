# CLAUDE S81-PH gather: 128 root chain tiles, abutted columns (tools/s81_ph/s81_ph_gather_plan.py)
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_c\\?\[(\d+)\\?\]\.g_k\\?\[(\d+)\\?\]\.u_t$} $ot_nm -> ot_c ot_k]} { continue }
  set ot_x [expr {21.6 + $ot_c * 237.6}]
  set ot_y [expr {10.8 + $ot_k * 125.28}]
  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation R0
  incr ot_n
}
if {$ot_n != 128} { error "place_tiles: placed $ot_n tiles, expected 128" }
puts "place_tiles: $ot_n tiles placed"
