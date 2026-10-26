# fe-push-ds-1010 2026-10-10 dsfd_wfc_crp (302.4 x 237.6, signal pins on ALL four faces): the 3 link-in landing macros
# (ot_sram_1r1w_128x256_m1_r2c2, 94.824 x 41.064, pins on the W and E short edges) in ONE interior column, centred:
# x 103.68 (103.7 um W channel / 103.9 um E channel for the macro pins + the W/E pin-flop logic), rows y 36.72 / 95.04 /
# 153.36 (17.3 um channels between macros; 36.7 um S / 43.2 um N channels to the kit faces).  No macro within 36 um of
# a pin face (fe-wfccrp r2 FLOORPLAN_MARGIN macro_edge: the auto placer put tile 0 9.6 um from the S face, 489 pins
# behind it).  Grid 0.216 x / 0.27 rows.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {u_li\.u_f\.g_tile\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_t]} { continue }
  place_macro -macro_name $ot_nm -location [list 103.68 [expr {36.72 + 58.32 * $ot_t}]] -orientation R0
  incr ot_n
}
if {$ot_n != 3} { error "place_macros_wfccrp: placed $ot_n macros (expected 3)" }
puts "place_macros_wfccrp: $ot_n macros placed"
