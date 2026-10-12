# T_PBC (bank 0 / bank 2 column tile, 211.68 x 369.36): 6 macros stacked, 19.44 um row gaps, 6.48 um to the pin-less bottom, 19.44 um to the N (read) face, groups 0..5 bottom to top (pairs adjacent).
# el1011-ds-misc/engram 2026-10-11.  SRAM pins (clk / r_* / w_ce / w_addr / rd_out / most wd_in) face W into a 19.872 um
# access channel holding the per-macro W3 / R2 / capture flops; x = 0 mod 0.432, y = 0 mod 2.16 (M4 / M5 pin tracks).
set loc {{19.872 6.480} {19.872 66.960} {19.872 127.440} {19.872 187.920} {19.872 248.400} {19.872 308.880}}
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
