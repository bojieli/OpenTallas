# DIE-HBM-20 qcore_r13 V3a: W column, MY (rd_out/wd 137 side faces the logic), separated 105 um
foreach {inst master x y orient} {
  {u_fcore.u_red.ma} ot_sram_1r1w_128x256_m1_r2c2 15.12 191.664 MY
  {u_fcore.u_red.mb} ot_sram_1r1w_128x256_m1_r2c2 15.12 44.988 MY
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
