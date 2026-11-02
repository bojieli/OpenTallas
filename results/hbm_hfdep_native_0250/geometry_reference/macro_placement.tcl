foreach {inst master x y orient} {
  {u_fcore.u_rxb.g_block\[0\].u_block.g_mem\[0\].u_mem.u_sram} ot_sram_1r1w_64x512_m1_r2c2 17.28 47.532 MY
  {u_fcore.u_rxb.g_block\[1\].u_block.g_mem\[0\].u_mem.u_sram} ot_sram_1r1w_64x512_m1_r2c2 239.112 47.532 R0
  {u_fcore.u_rxb.g_block\[0\].u_block.g_mem\[1\].u_mem.u_sram} ot_sram_1r1w_64x512_m1_r2c2 17.28 146.892 MY
  {u_fcore.u_rxb.g_block\[1\].u_block.g_mem\[1\].u_mem.u_sram} ot_sram_1r1w_64x512_m1_r2c2 239.112 146.892 R0
} {
  place_macro -macro_name $inst -location [list $x $y] -orientation $orient -exact
}
