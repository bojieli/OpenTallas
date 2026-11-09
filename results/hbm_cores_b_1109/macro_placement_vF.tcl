# HBM-Q2NF-RF vF: vD ring +77.76 um in x, y on M4 tracks (0.012 mod 0.048); W strip 108 um.
foreach {inst master x y orient} {
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[0\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 112.320 77.772 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[1\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 112.320 120.972 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[2\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 112.320 164.172 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[3\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 112.320 207.372 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[0\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 695.520 77.772 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[1\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 695.520 120.972 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[2\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 695.520 164.172 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[3\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 695.520 207.372 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[0\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r0c0_g256 112.320 34.572 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[0\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r0c0_g256 112.320 248.412 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[1\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r0c0_g256 346.488 34.572 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[1\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r0c0_g256 346.488 248.412 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[2\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r0c0_g256 580.656 34.572 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[2\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r0c0_g256 580.656 248.412 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[1\].u_sram} ot_sram_1rw_256x64_m4_r2c2 267.840 110.604 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[0\].u_sram} ot_sram_1rw_256x64_m4_r2c2 527.904 110.604 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[2\].u_sram} ot_sram_1rw_256x64_m4_r2c2 267.840 188.364 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[3\].u_sram} ot_sram_1rw_256x64_m4_r2c2 527.904 188.364 R0
  {u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow} ot_sram_1rw_256x64_m4_r2c2 399.600 77.772 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
