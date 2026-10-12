# fe-push-qwen-1010 (2026-10-10): the embedding row-buffer SRAM of ot_qfd_sp_su64_sfu_bv RSRAM=1 (u_emb.g_rsram.u_rb,
# one ot_sram_1r1w_64x512_m1_r2c2, 171.288 x 77.760).  Placed 108 um off the W face (the eq_* / ea_* pins: the 512-bit
# write data arrives from there) and centred in y; the 512-bit read word fans out to the 64 lane decoders across the tile.
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set H [expr {double([$die yMax]) / $dbu}]
set x [expr {floor(108.0 / 0.216) * 0.216}]
set y [expr {floor(($H - 77.76) / 2.0 / 0.27) * 0.27}]
set ms {}
foreach i [$b getInsts] { if {[[$i getMaster] isBlock]} { lappend ms [$i getName] } }
if {[llength $ms] != 1} { error "su64_rsram_place requires exactly one SRAM: [llength $ms]" }
place_macro -macro_name [lindex $ms 0] -location [list $x $y] -orientation R0
