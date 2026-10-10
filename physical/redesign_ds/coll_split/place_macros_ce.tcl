# redesign-ds 2026-10-09: the 24 engine FIFO macros (ot_sram_1r1w_256x256_m2_r2c2, 172.824 x 41.064, pins on the W edge)
# of dsfd_coll_ce (680.4 x 680.4, middle tile of the three-tile collective core) in TWO columns of 12 rows: FIFO
# (src s, par p, tile t) -> r = 6 s + 3 p + t; column r / 12 at x 60.48 / 353.376 (0.216 grid), row r % 12 at
# y 10.8 + 55.08 row (14-um channels).  W channel 60 um (lanes 1 / 2 logic + column A pins), middle channel 120 um
# (column B pins), E channel 154 um (lanes 5 / 6 logic).
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_src\\?\[(\d)\\?\]\.g_par\\?\[(\d)\\?\]\..*g_tile\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_s ot_p ot_t]} { continue }
  set ot_r [expr {6 * $ot_s + 3 * $ot_p + $ot_t}]
  set ot_x [expr {($ot_r / 12) == 0 ? 60.48 : 353.376}]
  place_macro -macro_name $ot_nm -location [list $ot_x [expr {10.8 + 55.08 * ($ot_r % 12)}]] -orientation R0
  incr ot_n
}
if {$ot_n != 24} { error "place_macros_ce: placed $ot_n macros (expected 24)" }
puts "place_macros_ce: $ot_n macros placed"
