foreach {inst master x y orient} {
  {g_t\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 17.28 17.292 R0
  {g_t\[1\].u_m} ot_sram_1r1w_128x256_m1_r2c2 17.28 67.02 R0
  {g_t\[2\].u_m} ot_sram_1r1w_128x256_m1_r2c2 17.28 118.956 R0
  {g_t\[3\].u_m} ot_sram_1r1w_128x256_m1_r2c2 17.28 168.684 R0
  {g_t\[4\].u_m} ot_sram_1r1w_128x256_m1_r2c2 147.096 17.292 R0
  {g_t\[5\].u_m} ot_sram_1r1w_128x256_m1_r2c2 147.096 67.02 R0
  {g_t\[6\].u_m} ot_sram_1r1w_128x256_m1_r2c2 147.096 118.956 MY
  {g_t\[7\].u_m} ot_sram_1r1w_128x256_m1_r2c2 147.096 168.684 MY
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
