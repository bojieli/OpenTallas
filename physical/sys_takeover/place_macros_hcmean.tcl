# sys-takeover 2026-10-09: ot_dsrom_hc_mean_capture (SINGLE_CAPTURE, 400 x 320): 3 x ot_sram_1r1w_256x256_m2_r2c2
# (172.824 x 41.064) in one centred column, >= 60 um from every pin edge, 14 um row gaps (>= 12 um sliver rule).
# hcmean_mreg_a-94e3662f3 failed fp-lint macro_edge (auto placement put g_sram[0] 5.2 um from the S pin edge).
set ot_n 0
foreach ot_i [[ord::get_db_block] getInsts] {
  set ot_nm [$ot_i getName]
  if {![regexp {g_sram\\?\[(\d)\\?\]\.u_mem$} $ot_nm -> ot_b]} { continue }
  place_macro -macro_name $ot_nm -location [list 113.616 [expr {60.21 + $ot_b * 55.08}]] -orientation R0
  incr ot_n
}
if {$ot_n != 3} { error "place_macros_hcmean: placed $ot_n macros, expected 3" }
