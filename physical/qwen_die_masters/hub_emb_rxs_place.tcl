# fe-push-qwen-1010 (2026-10-10): the eight receive-buffer SRAMs of ot_qwen_die_hub_emb RXS=1 (link k: u.g_rx[k].u_rx.
# g_rxs.g_m[0/1].u_ib, ot_sram_1r1w_128x256_m1_r2c2 94.824 x 41.040, clock fck[k]).  Each link's pair sits side by side
# (12.96 um channel) 100 um in from the E face, centred on that link's E-face pin window (l2 5.4-84.4, l3 245-324,
# l0 326.7-439.7, l1 442.4-555.4), clamped >= 30 um off the S edge; the 512-bit write data arrives from those pins.
set b [ord::get_db_block]
set die [$b getDieArea]
set dbu [[ord::get_db_tech] getDbUnitsPerMicron]
set W [expr {double([$die xMax]) / $dbu}]
set H [expr {double([$die yMax]) / $dbu}]
set mw 94.824; set mh 41.04; set ch 12.96
set x1 [expr {floor(($W - 100.0 - $mw) / 0.216) * 0.216}]
set x0 [expr {floor(($x1 - $ch - $mw) / 0.216) * 0.216}]
array set yc {0 383.2 1 498.9 2 44.9 3 284.5}
set n 0
foreach i [$b getInsts] {
  if {![[$i getMaster] isBlock]} continue
  set nm [$i getName]
  if {![regexp {g_rx\D*([0-3])\D.*g_m\D*([01])\D} $nm -> k m]} { error "hub_emb_rxs_place: unexpected macro $nm" }
  set y [expr {$yc($k) - $mh / 2.0}]
  if {$y < 30.0} { set y 30.0 }
  set y [expr {floor($y / 0.27) * 0.27}]
  set x [expr {$m == 0 ? $x0 : $x1}]
  place_macro -macro_name $nm -location [list $x $y] -orientation R0
  incr n
}
if {$n != 8} { error "hub_emb_rxs_place placed $n SRAMs, expected 8" }
