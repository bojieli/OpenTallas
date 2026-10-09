# S81-PH tiles, gap >= 12 um (drive-2125 2026-10-08, template F, 0 cycles): place_macros_tile.tcl with the macro pitch
# 183.6 -> 184.896 um (856 x 0.216 grid), so the 172.824-um macros leave a 12.07-um gap (was 10.78: fp_lint sliver on
# dsfd_colt_lane u_q.g_m[0].u_m | g_m[1].u_m).  Same row, R0, y = 5.4; the 2-macro tile ends at x 379.3 of 432.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_(?:m|tile)\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_k]} { continue }
  place_macro -macro_name $ot_nm -location [list [expr {21.6 + $ot_k * 184.896}] 5.4] -orientation R0
  incr ot_n
}
if {$ot_n < 2} { error "place_macros_tile_g12: placed $ot_n macros" }
puts "place_macros_tile_g12: $ot_n macros placed (pitch 184.896)"
