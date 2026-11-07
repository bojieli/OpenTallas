# HBM-HARD-1-IDX vL: W column pitch 49.728 so the N band over the W column is 19.4 um (was 7.2); banks follow their rr/wd pins.
foreach {inst master x y orient} {
  {u_fcore.u_dbk.L\[0\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 45.792 11.724 R0
  {u_fcore.u_dbk.L\[1\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 45.792 61.452 R0
  {u_fcore.u_dbk.L\[4\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 45.792 111.18 R0
  {u_fcore.u_dbk.L\[5\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 45.792 160.908 R0
  {u_fcore.u_dbk.L\[6\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 45.792 210.636 R0
  {u_fcore.u_cp.g_tab\[0\].u_tab} ot_sram_1r1w_128x256_m1_r2c2 232.2 11.724 R0
  {u_fcore.u_cp.g_tab\[1\].u_tab} ot_sram_1r1w_128x256_m1_r2c2 232.2 61.452 R0
  {u_fcore.u_dbk.L\[2\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 232.2 111.18 R0
  {u_fcore.u_dbk.L\[3\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 232.2 160.908 R0
  {u_fcore.u_dbk.L\[7\].u_bank.landing} ot_sram_1r1w_128x256_m1_r2c2 232.2 210.636 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
