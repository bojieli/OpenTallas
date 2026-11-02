# PREP ONLY: NOT installed/admitted. Actual mapped four SRAM names and native LEF.
foreach {inst master x y orient} {
  {u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro[0].u_s} ot_sram_1r1w_128x256_m1_r2c2 17.28 17.28 R0
  {u_ref.u_leaf.u_a.u.u.g_static_rows.u_rows.g_data.g_macro[1].u_s} ot_sram_1r1w_128x256_m1_r2c2 131.52 17.28 R0
  {u_ref.u_leaf.u_b.u.g_static_rows.u_rows.g_data.g_macro[0].u_s} ot_sram_1r1w_128x256_m1_r2c2 17.28 114.432 R0
  {u_ref.u_leaf.u_b.u.g_static_rows.u_rows.g_data.g_macro[1].u_s} ot_sram_1r1w_128x256_m1_r2c2 131.52 114.432 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
