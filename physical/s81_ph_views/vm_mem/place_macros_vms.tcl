# CLAUDE s81-blocks 2026-10-07: explicit, site-aligned macro grid for the bit-sliced VM tiles (dsfd_vm_bgh: 8 banks x
# 2 macro columns in 507.588 x 500.04; dsfd_vm_bgq: 8 x 1 in 253.794 x 500.04).  Bank gb on row gb (y = 4.32 +
# 61.56 gb), macro column gc at x = 43.2 / 289.872 (bgh) or 39.744 (bgq): 0.216-um x grid, 1.08-um y grid, 27-32 um
# channels between rows for the bank logic (vm_bg h600 / coll_core failed DPL-0033 with rtl_macro_placer).
set ot_w [expr {[[[ord::get_db_block] getDieArea] dx] / double([[ord::get_db_block] getDbUnitsPerMicron])}]
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_bank\\?\[(\d+)\\?\]\.g_m\\?\[(\d)\\?\]\..*u_m$} $ot_nm -> ot_b ot_c]} { continue }
  if {$ot_w > 400} { set ot_x [expr {$ot_c == 0 ? 43.2 : 289.872}] } else { set ot_x 39.744 }
  place_macro -macro_name $ot_nm -location [list $ot_x [expr {4.32 + $ot_b * 61.56}]] -orientation R0
  incr ot_n
}
if {$ot_n < 8} { error "place_macros_vms: placed $ot_n macros" }
puts "place_macros_vms: $ot_n macros placed (die width $ot_w)"
