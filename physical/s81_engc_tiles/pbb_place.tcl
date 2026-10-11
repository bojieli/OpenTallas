# T_PBB (bank 1 band tile, 582.336 x 120.96): 3 columns x 2 rows, pair k = column k (groups 2k / 2k+1 stacked).
# el1011-ds-misc/engram 2026-10-11.  SRAM pins (clk / r_* / w_ce / w_addr / rd_out / most wd_in) face W into a 19.872 um
# access channel holding the per-macro W3 / R2 / capture flops; x = 0 mod 0.432, y = 0 mod 2.16 (M4 / M5 pin tracks).
set loc {{19.872 8.640} {19.872 69.120} {212.544 8.640} {212.544 69.120} {405.216 8.640} {405.216 69.120}}
set b [ord::get_db_block]
set count 0
foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {
    if {![regexp {g_grp\D*(\d+)} [$i getName] -> k]} { error "pbb_place: unexpected macro [$i getName]" }
    set xy [lindex $loc $k]
    place_macro -macro_name [$i getName] -location $xy -orientation R0 -exact
    incr count
  }
}
if {$count != 6} { error "pbb_place: placed $count macros, expected 6" }
