foreach {inst master x y orient} {
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[0\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r2c2 306.672 321.804 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[0\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r2c2 306.672 280.668 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[1\].u_sram} ot_sram_1rw_256x64_m4_r2c2 359.904 262.764 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[0\].u_sram} ot_sram_1rw_256x64_m4_r2c2 359.904 244.86 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[1\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r2c2 306.672 380.172 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[1\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r2c2 306.672 421.308 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[2\].u_bank.u_sram_lo} ot_sram_1r1w_256x256_m2_r2c2 306.672 462.444 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_mem\[2\].u_bank.u_sram_hi} ot_sram_1r1w_256x256_m2_r2c2 306.672 503.58 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[2\].u_sram} ot_sram_1rw_256x64_m4_r2c2 359.904 544.716 R0
  {u_fcore.u_x.u_body.g_iss256.u_issuer.g_meta\[3\].u_sram} ot_sram_1rw_256x64_m4_r2c2 359.904 562.62 R0
  {u_fcore.u_x.u_body.g_q2.n_u_fj.u_fj.u.u_program.g_fsram.u_flow} ot_sram_1rw_256x64_m4_r2c2 359.904 580.524 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[0\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 75.552 210.492 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[1\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 75.552 288.348 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[2\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 75.552 377.004 R0
  {u_fcore.u_x.u_body.g_link\[0\].u_link.g_bank\[3\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 75.552 454.86 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[0\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 539.328 210.492 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[1\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 539.328 288.348 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[2\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 539.328 377.004 R0
  {u_fcore.u_x.u_body.g_link\[1\].u_link.g_bank\[3\].u_store.u_native.u_sram} ot_sram_1r1w_64x512_m1_r2c2 539.328 454.86 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
