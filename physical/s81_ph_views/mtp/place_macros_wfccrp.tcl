# mtp-wfc 2026-10-10 (dsfd_wfc_crp fe-wfccrp-c0b1a95f4 FLOORPLAN_MARGIN macro_edge: the auto macro placer put a landing
# SRAM 9.6 um from the S pin face with 489 signal pins behind it).  The tile has pins on ALL four faces (W die link,
# E VM, N kit link, S kit VM + clocks), so the three 94.824 x 41.064 landing SRAMs go in ONE interior column centred in
# the 302.4 x 237.6 outline: x 103.788 (103.8 um channels to W and E), y 43.2 / 98.28 / 153.36 (43.2 um channels to S
# and N, 14.0 um gaps >= the 12 um sliver rule), R0.  Layout only, 0 cycles.
set ot_y {43.2 98.28 153.36}
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_tile\\?\[(\d+)\\?\].*u_m$} $ot_nm -> ot_t]} { continue }
  if {![$ot_i isBlock]} { continue }
  place_macro -macro_name $ot_nm -location [list 103.788 [lindex $ot_y $ot_t]] -orientation R0
  incr ot_n
}
if {$ot_n != 3} { error "place_macros_wfccrp: placed $ot_n macros, expected 3" }
puts "place_macros_wfccrp: $ot_n macros placed"
