# CLAUDE S81-PH collector: the 8 frame-buffer SRAM macros (ot_sram_1r1w_256x256_m2_r2c2, 172.824 x 41.064) at the slab
# centre, where the 7 transport stages from the W / E input faces end and the merger sits (col_m1: rtl_macro_placer put
# them in the W edge corner -> GRT-0116 overflow on the rq nets there).  W stacks (SW 0, NW 2) left of a 86 um centre
# channel, E stacks (SE 1, NE 3) right; S stacks on the lower row, N stacks on the upper row; R0, 0.216 um grid.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_in\\?\[(\d)\\?\]\.u_in\.u_q\.g_tile\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_l ot_t]} { continue }
  set ot_e [expr {$ot_l % 2}]
  set ot_nn [expr {$ot_l / 2}]
  set ot_x [expr {$ot_e ? (2678.4 + $ot_t * 194.4) : (2224.8 + $ot_t * 194.4)}]
  set ot_y [expr {$ot_nn ? 453.6 : 345.6}]
  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation R0
  incr ot_n
}
if {$ot_n != 8} { error "place_macros: placed $ot_n macros, expected 8" }
puts "place_macros: $ot_n macros placed"
