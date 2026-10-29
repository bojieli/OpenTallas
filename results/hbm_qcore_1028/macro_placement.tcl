foreach {inst master x y orient} {
  {u_fcore.u_red.ma} ot_sram_1r1w_128x256_m1_r2c2 64.8 133.92 R0
  {u_fcore.u_red.mb} ot_sram_1r1w_128x256_m1_r2c2 64.8 34.56 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
