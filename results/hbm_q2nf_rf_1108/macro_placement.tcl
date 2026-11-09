# HBM-Q2NF-RF vE: plan outline/pins; macros off W+N faces, issuer stack south, y on M4 tracks (y = 0.012 mod 0.048).
foreach {inst master x y orient} {
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[0\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 133.008 239.004 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[0\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 597.024 239.004 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[1\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 133.008 317.004 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[1\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 597.024 317.004 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[2\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 133.008 405.996 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[2\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 597.024 405.996 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[3\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 133.008 483.996 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[3\].u_store.u_native.u_sram} ot_sram_1r1w_64x141_m1_r0c0_g141 597.024 483.996 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[0\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r0c0_g256 308.400 55.980 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[0\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r0c0_g256 308.400 96.396 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[1\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r0c0_g256 308.400 136.764 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[1\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r0c0_g256 308.400 177.180 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[2\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r0c0_g256 308.400 217.548 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[2\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r0c0_g256 308.400 257.964 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[1\].u_sram} ot_sram_1rw_256x64_m4_r2c2 195.000 302.988 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[0\].u_sram} ot_sram_1rw_256x64_m4_r2c2 272.400 302.988 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[2\].u_sram} ot_sram_1rw_256x64_m4_r2c2 349.800 302.988 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[3\].u_sram} ot_sram_1rw_256x64_m4_r2c2 427.200 302.988 R0
  {u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow} ot_sram_1rw_256x64_m4_r2c2 504.600 302.988 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
