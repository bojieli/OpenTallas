# DIE-HBM-21 sfustore S1: SRAM-edge rule probe (heavy rd_out/wd W edge toward logic corridors), cols orient ['R0', 'MY', 'R0'] x [15.12, 116.424, 242.136]
foreach {inst master x y orient} {
  {u_fcore.g_bank\[0\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 15.120 15.132 R0
  {u_fcore.g_bank\[10\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 116.424 15.132 MY
  {u_fcore.g_bank\[11\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 242.136 15.132 R0
  {u_fcore.g_bank\[12\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 15.120 66.972 R0
  {u_fcore.g_bank\[13\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 116.424 66.972 MY
  {u_fcore.g_bank\[14\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 242.136 66.972 R0
  {u_fcore.g_bank\[15\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 15.120 118.86 R0
  {u_fcore.g_bank\[1\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 116.424 118.86 MY
  {u_fcore.g_bank\[2\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 242.136 118.86 R0
  {u_fcore.g_bank\[3\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 15.120 170.7 R0
  {u_fcore.g_bank\[4\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 116.424 170.7 MY
  {u_fcore.g_bank\[5\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 242.136 170.7 R0
  {u_fcore.g_bank\[6\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 15.120 222.588 R0
  {u_fcore.g_bank\[7\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 116.424 222.588 MY
  {u_fcore.g_bank\[8\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 242.136 222.588 R0
  {u_fcore.g_bank\[9\].u_bank.u_data.g_read\[0\].u_m} ot_sram_1r1w_128x256_m1_r2c2 15.120 274.428 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
