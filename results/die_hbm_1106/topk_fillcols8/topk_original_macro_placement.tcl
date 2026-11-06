foreach {inst master x y orient} {
  {u_fcore.u_core.u_sto.gm\[7\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.81 167.388 R0
  {u_fcore.u_core.u_sto.gm\[6\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.81 77.676 R0
  {u_fcore.u_core.u_sto.gm\[5\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.81 267.9 R0
  {u_fcore.u_core.u_sto.gm\[4\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.81 357.612 R0
  {u_fcore.u_core.u_sto.gm\[3\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.17 167.388 R0
  {u_fcore.u_core.u_sto.gm\[2\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.17 77.676 R0
  {u_fcore.u_core.u_sto.gm\[1\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.17 267.9 R0
  {u_fcore.u_core.u_sto.gm\[0\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.17 357.612 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
