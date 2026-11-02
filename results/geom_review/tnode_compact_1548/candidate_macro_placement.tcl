# PROPOSAL ONLY: exact current macro names/sizes, no source adoption.
foreach {inst master x y orient} {
  {u_pad.u_d} ot_sram_1r1w_128x256_m1_r2c2 15.168 8.796 R0
  {u_pad.u_c} ot_sram_1r1w2c_32x64_m1 15.168 69.372 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
