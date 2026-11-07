foreach {inst master x y orient} {
  {u_fcore.u_core.u_ot_pr_core.bank.u_a} ot_sram_1r1w_1024x256_m2_r2c2 47.616 76.38 R0
  {u_fcore.u_core.u_ot_pr_core.bank.u_b} ot_sram_1r1w_1024x256_m2_r2c2 47.616 164.172 R0
  {u_fcore.u_core.u_ot_pr_core.bank.u_c} ot_sram_1r1w_1024x256_m2_r2c2 47.616 234.732 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
