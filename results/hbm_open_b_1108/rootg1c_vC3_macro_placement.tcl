# ROOTG1C vC1: two facing 4-row towers of ot_sram_1r1w_128x128_m1_r0c0_g128 (left R0 write edge E, right MY write edge W, 29.976-um write channel); origins on 0.012 mod 0.048
# HBM-OPEN-B 11-08 vC3 = C2 + central channel 29.97 -> 43.6 um: left tower x 30.252 -> 25.932, right tower x 113.388 -> 123.756 (0.432 grid, 0.012 mod 0.048 pin alignment kept); C2 GRT-0116 overflow 141 at x 67-84, y 0-51 (S street turn into the channel). Same RTL, pins, clock, cycles 0; DO_NOT_COUNT until plan event for 2 clock pins.
foreach {inst master x y orient} {
  {u_fcore.u_grp.g_lane\[0\].u_payload.u_lo} ot_sram_1r1w_128x128_m1_r0c0_g128 25.932 14.892 R0
  {u_fcore.u_grp.g_lane\[0\].u_payload.u_hi} ot_sram_1r1w_128x128_m1_r0c0_g128 123.756 14.892 MY
  {u_fcore.u_grp.g_lane\[1\].u_payload.u_lo} ot_sram_1r1w_128x128_m1_r0c0_g128 25.932 42.492 R0
  {u_fcore.u_grp.g_lane\[1\].u_payload.u_hi} ot_sram_1r1w_128x128_m1_r0c0_g128 123.756 42.492 MY
  {u_fcore.u_grp.g_lane\[2\].u_payload.u_lo} ot_sram_1r1w_128x128_m1_r0c0_g128 25.932 70.092 R0
  {u_fcore.u_grp.g_lane\[2\].u_payload.u_hi} ot_sram_1r1w_128x128_m1_r0c0_g128 123.756 70.092 MY
  {u_fcore.u_grp.g_lane\[3\].u_payload.u_lo} ot_sram_1r1w_128x128_m1_r0c0_g128 25.932 97.692 R0
  {u_fcore.u_grp.g_lane\[3\].u_payload.u_hi} ot_sram_1r1w_128x128_m1_r0c0_g128 123.756 97.692 MY
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
