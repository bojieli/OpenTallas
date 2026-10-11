# T_PBC (bank 0 / bank 2 column tile, 196.992 x 360.72): 6 macros stacked, groups 0..5 bottom to top (pairs adjacent).
# el1011-ds-misc/engram 2026-10-11.  SRAM pins (clk / r_* / w_ce / w_addr / rd_out / most wd_in) face W into a 19.872 um
# access channel holding the per-macro W3 / R2 / capture flops; x = 0 mod 0.432, y = 0 mod 2.16 (M4 / M5 pin tracks).
set loc {{19.872 8.640} {19.872 69.120} {19.872 129.600} {19.872 190.080} {19.872 250.560} {19.872 311.040}}
set b [ord::get_db_block]
set count 0
foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {
    if {![regexp {g_grp\D*(\d+)} [$i getName] -> k]} { error "pbc_place: unexpected macro [$i getName]" }
    set xy [lindex $loc $k]
    place_macro -macro_name [$i getName] -location $xy -orientation R0 -exact
    incr count
  }
}
if {$count != 6} { error "pbc_place: placed $count macros, expected 6" }
