# DIE-HBM-21 Q2d: V3a + lower macro down 4.32 (y 40.668)
foreach {inst master x y orient} {
  {u_fcore.u_red.ma} ot_sram_1r1w_128x256_m1_r2c2 15.12 191.664 MY
  {u_fcore.u_red.mb} ot_sram_1r1w_128x256_m1_r2c2 15.12 40.668 MY
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
