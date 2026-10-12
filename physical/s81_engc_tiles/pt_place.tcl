# Pair tile (233.28 x 120.96): groups 2k (row 0) / 2k+1 (row 1), W access channel 19.872 um, E margin 40.6 um.
# el1011-ds-misc/engram 2026-10-11.  SRAM pins (clk / r_* / w_ce / w_addr / rd_out / most wd_in) face W into a 19.872 um
# access channel holding the per-macro W3 / R2 / capture flops; x = 0 mod 0.432, y = 0 mod 2.16 (M4 / M5 pin tracks).
set loc {{19.872 8.640} {19.872 69.120}}
set b [ord::get_db_block]
set count 0
foreach i [$b getInsts] {
  if {[[$i getMaster] isBlock]} {
    if {![regexp {g_grp\D*(\d+)} [$i getName] -> k]} { error "pt_place: unexpected macro [$i getName]" }
    set xy [lindex $loc $k]
    place_macro -macro_name [$i getName] -location $xy -orientation R0 -exact
    incr count
  }
}
if {$count != 2} { error "pt_place: placed $count macros, expected 2" }
