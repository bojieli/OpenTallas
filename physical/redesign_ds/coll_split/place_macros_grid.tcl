# el1011-ds-coll 2026-10-11: MACRO_PLACEMENT_TCL for the hardened collective tiles (contract_cbh / contract_ceh).
# Places every macro instance (master type BLOCK) on a column-major grid with >= 20 um channels and core margins
# (physical spec: el1011-ds-coll.log).  Parameters (ORFS variables / env):
#   OT_MG_N   expected macro count     OT_MG_ROWS  rows per column
#   OT_MG_X0 / OT_MG_Y0  first macro origin (um)   OT_MG_DX / OT_MG_DY  pitch (um; site / row aligned)
# Origins must keep macro pins on the asap7 track grid (SUBMIT_LINT MACRO_GRID; tools/check_macro_track_alignment.py):
#   ot_sram_1r1w_128x256_m1_r2c2 R0 needs x = 0.024 mod 0.048 and y = 0 mod 0.048, so Y0/DY are multiples of 0.048
#   (e.g. X0=20.088 Y0=20.256 DX=114.804 DY=61.296; Y0=20.250 / DY=61.290 left all 819 signal pins off-track).
set ot_n 0
set ot_ms {}
foreach ot_i [[ord::get_db_block] getInsts] {
  if {[[$ot_i getMaster] getType] eq "BLOCK"} { lappend ot_ms [$ot_i getName] }
}
set ot_ms [lsort -dictionary $ot_ms]
foreach ot_nm $ot_ms {
  set ot_c [expr {$ot_n / $::env(OT_MG_ROWS)}]; set ot_r [expr {$ot_n % $::env(OT_MG_ROWS)}]
  set ot_x [expr {$::env(OT_MG_X0) + $ot_c * $::env(OT_MG_DX)}]
  set ot_y [expr {$::env(OT_MG_Y0) + $ot_r * $::env(OT_MG_DY)}]
  place_macro -macro_name $ot_nm -location [list $ot_x $ot_y] -orientation R0
  incr ot_n
}
if {$ot_n != $::env(OT_MG_N)} { error "place_macros_grid: placed $ot_n macros (expected $::env(OT_MG_N))" }
puts "place_macros_grid: $ot_n macros placed"
