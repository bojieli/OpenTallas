foreach {inst master x y orient} {
  {m0.g_bank\[0\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 17.292 R0
  {m0.g_bank\[1\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 17.292 R0
  {m0.g_bank\[2\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 17.292 R0
  {m0.g_bank\[3\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 17.292 R0
  {m0.g_bank\[4\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 66.972 R0
  {m0.g_bank\[5\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 66.972 R0
  {m0.g_bank\[6\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 66.972 R0
  {m0.g_bank\[7\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 66.972 R0
  {m0.g_bank\[8\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 116.7 R0
  {m0.g_bank\[9\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 116.7 R0
  {m0.g_bank\[10\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 116.7 R0
  {m0.g_bank\[11\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 116.7 R0
  {m0.g_bank\[12\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 166.38 R0
  {m0.g_bank\[13\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 166.38 R0
  {m0.g_bank\[14\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 166.38 R0
  {m0.g_bank\[15\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 166.38 R0
  {m1.g_bank\[0\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 216.108 R0
  {m1.g_bank\[1\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 216.108 R0
  {m1.g_bank\[2\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 216.108 R0
  {m1.g_bank\[3\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 216.108 R0
  {m1.g_bank\[4\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 265.788 R0
  {m1.g_bank\[5\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 265.788 R0
  {m1.g_bank\[6\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 265.788 R0
  {m1.g_bank\[7\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 265.788 R0
  {m1.g_bank\[8\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 315.516 R0
  {m1.g_bank\[9\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 315.516 R0
  {m1.g_bank\[10\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 315.516 R0
  {m1.g_bank\[11\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 315.516 R0
  {m1.g_bank\[12\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 17.28 365.196 R0
  {m1.g_bank\[13\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 198.744 365.196 R0
  {m1.g_bank\[14\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 380.208 365.196 R0
  {m1.g_bank\[15\].u_b.g_m11.u_m} ot_sram_1r1w_256x256_m2_r2c2 561.672 365.196 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
