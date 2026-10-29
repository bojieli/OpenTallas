# DIE-HBM-20 qcore_r13 V3c: one N row (centre clock entry 133.9,125.3 stays free), both MY, gap 21.6 um
foreach {inst master x y orient} {
  {u_fcore.u_red.ma} ot_sram_1r1w_128x256_m1_r2c2 15.12 191.664 MY
  {u_fcore.u_red.mb} ot_sram_1r1w_128x256_m1_r2c2 131.544 191.664 MY
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
