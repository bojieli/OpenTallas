foreach {inst master x y orient} {
  {u_fcore.core.gq\[0\].gm\[2\].mem} ot_sram_1r1w_256x256_m2_r2c2 68.526 75.468 MY
  {u_fcore.core.gq\[0\].gm\[1\].mem} ot_sram_1r1w_256x256_m2_r2c2 68.526 125.196 MY
  {u_fcore.core.gq\[0\].gm\[0\].mem} ot_sram_1r1w_256x256_m2_r2c2 68.526 174.876 MY
  {u_fcore.core.gq\[1\].gm\[0\].mem} ot_sram_1r1w_256x256_m2_r2c2 68.526 233.340 MY
  {u_fcore.core.gq\[1\].gm\[1\].mem} ot_sram_1r1w_256x256_m2_r2c2 68.526 283.020 MY
  {u_fcore.core.gq\[1\].gm\[2\].mem} ot_sram_1r1w_256x256_m2_r2c2 68.526 332.748 MY
  {u_fcore.core.gq\[2\].gm\[2\].mem} ot_sram_1r1w_256x256_m2_r2c2 358.830 75.468 R0
  {u_fcore.core.gq\[2\].gm\[1\].mem} ot_sram_1r1w_256x256_m2_r2c2 358.830 125.196 R0
  {u_fcore.core.gq\[2\].gm\[0\].mem} ot_sram_1r1w_256x256_m2_r2c2 358.830 174.876 R0
  {u_fcore.core.gq\[3\].gm\[0\].mem} ot_sram_1r1w_256x256_m2_r2c2 358.830 233.340 R0
  {u_fcore.core.gq\[3\].gm\[1\].mem} ot_sram_1r1w_256x256_m2_r2c2 358.830 283.020 R0
  {u_fcore.core.gq\[3\].gm\[2\].mem} ot_sram_1r1w_256x256_m2_r2c2 358.830 332.748 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
