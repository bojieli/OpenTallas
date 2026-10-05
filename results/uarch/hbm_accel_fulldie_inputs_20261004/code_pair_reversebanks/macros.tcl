# Post-link/floorplan macro-placement hook; exact20 masters/hierarchies.
proc ot_code_pair_instance {literal master} {
 set block [ord::get_db_block]
 foreach inst [$block getInsts] {
  if {[string map {\\ ""} [$inst getName]] eq $literal} {
   if {[[$inst getMaster] getName] ne $master} {error "Wrong macro master: $literal"}
   return [$inst getName]
  }
 }
 error "Missing actual CODE macro: $literal"
}
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[0].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 395.280000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[0].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 395.280000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[1].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 298.620000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[1].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 298.620000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[2].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 201.960000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[2].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 201.960000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[3].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 105.300000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[3].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 105.300000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[4].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 8.640000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[0].bank[4].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 8.640000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[0].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 395.280000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[0].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 395.280000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[1].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 298.620000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[1].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 298.620000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[2].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 201.960000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[2].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 201.960000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[3].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 105.300000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[3].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 105.300000} -orientation R0
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[4].data_store} ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 8.640000} -orientation MY
place_macro -macro_name [ot_code_pair_instance {u_leaf.on.column[1].bank[4].check_store} ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 8.640000} -orientation R0
