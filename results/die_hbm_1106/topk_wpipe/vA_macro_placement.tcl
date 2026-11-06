# HBM-FORM-SPLIT-13-TOPK vA macro placement (hand form; y on the M4 pin track grid 0.048k+0.012, x on the 0.054 site grid)
foreach {inst master x y orient} {
  {u_fcore.u_core.u_sto.gm\[6\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.810 47.484 MY
  {u_fcore.u_core.u_sto.gm\[7\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.810 168.444 MY
  {u_fcore.u_core.u_sto.gm\[5\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.810 289.404 MY
  {u_fcore.u_core.u_sto.gm\[4\].mem} ot_sram_1r1w_64x512_m1_r2c2 81.810 410.364 MY
  {u_fcore.u_core.u_sto.gm\[2\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.170 47.484 R0
  {u_fcore.u_core.u_sto.gm\[3\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.170 168.444 R0
  {u_fcore.u_core.u_sto.gm\[1\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.170 289.404 R0
  {u_fcore.u_core.u_sto.gm\[0\].mem} ot_sram_1r1w_64x512_m1_r2c2 397.170 410.364 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
