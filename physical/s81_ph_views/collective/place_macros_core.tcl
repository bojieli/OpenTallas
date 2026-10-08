# CLAUDE s81-blocks 2026-10-07: explicit site-aligned macro column for dsfd_coll_core (507.384 x 1360.8; 24 frame-FIFO
# macros ot_sram_1r1w_256x256_m2_r2c2 172.824 x 41.064): one central column, FIFO (src, par) tiles 0..2 on rows
# 6 src + 3 par + tile, y = 10.8 + 55.08 row, x = 167.184 (0.216-um x grid, 1.08-um y grid): ~167 um logic / pin
# channels to the W and E lane faces.  s81ph-dsfd_coll_core-a53f40362 crashed twice in DPL (390 site-alignment
# problems, 178 overlaps) after rtl_macro_placer.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_src\\?\[(\d)\\?\]\.g_par\\?\[(\d)\\?\]\..*g_tile\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_s ot_p ot_t]} { continue }
  set ot_r [expr {6 * $ot_s + 3 * $ot_p + $ot_t}]
  place_macro -macro_name $ot_nm -location [list 167.184 [expr {10.8 + 55.08 * $ot_r}]] -orientation R0
  incr ot_n
}
if {$ot_n != 24} { error "place_macros_core: placed $ot_n macros (expected 24)" }
puts "place_macros_core: $ot_n macros placed"
