# sys-takeover 2026-10-09: ot_hbm_tu_retry_phy_port (NOEPOCH) 24 x ot_sram_1r1w_128x256_m1_r2c2 (94.824 x 41.04).
# pi-turetryphy-c7c53c4c2 failed fp-lint macro_edge (macros 2.2 um from pin edges) + sliver.  Grid 4 columns x 6 rows,
# >= 30 um from every die edge (pin channels), column gap 20.2 um, row gap 14.0 um (>= 12 um sliver rule).
#   ingress (2 banks x 4 macros) rows 0-1; retry storage (4 banks x 4 macros) rows 2-5;  column = macro index.
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {(u_ingress|u_retry)\.u_\w+\.g_bank\\?\[(\d)\\?\]\.g_macro\\?\[(\d)\\?\]\.u_mem$} $ot_nm -> ot_w ot_b ot_m]} { continue }
  set ot_r [expr {$ot_w eq "u_ingress" ? $ot_b : 2 + $ot_b}]
  place_macro -macro_name $ot_nm -location [list [expr {30.24 + $ot_m * 115.02}] [expr {29.97 + $ot_r * 55.08}]] -orientation R0
  incr ot_n
}
if {$ot_n != 24} { error "place_macros_turetry: placed $ot_n macros, expected 24" }
puts "place_macros_turetry: $ot_n macros placed"
