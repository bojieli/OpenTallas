# Margin CODE pair: the SAME 20 macro locations/orientations as the retained
# slot (results/uarch/hbm_accel_fulldie_inputs_20261004/code_pair_slot/macros.tcl),
# bound to the per-bank kept hierarchy on.column[p].bank[b].u_bank.
proc ot_cpm_instance {p b kind master} {
 set found {}
 foreach inst [[ord::get_db_block] getInsts] {
  set n [string map {\\ ""} [$inst getName]]
  if {[regexp "column\\\[$p\\\]\\.bank\\\[$b\\\]\\.u_bank\[/.\]${kind}_store\$" $n]} {lappend found $inst}
 }
 if {[llength $found]!=1} {error "CODE margin macro p$p b$b $kind: found [llength $found]"}
 set inst [lindex $found 0]
 if {[[$inst getMaster] getName] ne $master} {error "Wrong macro master p$p b$b $kind"}
 return [$inst getName]
}
place_macro -macro_name [ot_cpm_instance 0 0 data ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 8.640000} -orientation MY
place_macro -macro_name [ot_cpm_instance 0 0 check ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 8.640000} -orientation R0
place_macro -macro_name [ot_cpm_instance 0 1 data ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 105.300000} -orientation MY
place_macro -macro_name [ot_cpm_instance 0 1 check ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 105.300000} -orientation R0
place_macro -macro_name [ot_cpm_instance 0 2 data ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 201.960000} -orientation MY
place_macro -macro_name [ot_cpm_instance 0 2 check ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 201.960000} -orientation R0
place_macro -macro_name [ot_cpm_instance 0 3 data ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 298.620000} -orientation MY
place_macro -macro_name [ot_cpm_instance 0 3 check ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 298.620000} -orientation R0
place_macro -macro_name [ot_cpm_instance 0 4 data ot_sram_1r1w_1024x256_m2_r2c2] -location {8.640000 395.280000} -orientation MY
place_macro -macro_name [ot_cpm_instance 0 4 check ot_sram_1r1w_128x256_m1_r2c2] -location {287.064000 395.280000} -orientation R0
place_macro -macro_name [ot_cpm_instance 1 0 data ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 8.640000} -orientation MY
place_macro -macro_name [ot_cpm_instance 1 0 check ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 8.640000} -orientation R0
place_macro -macro_name [ot_cpm_instance 1 1 data ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 105.300000} -orientation MY
place_macro -macro_name [ot_cpm_instance 1 1 check ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 105.300000} -orientation R0
place_macro -macro_name [ot_cpm_instance 1 2 data ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 201.960000} -orientation MY
place_macro -macro_name [ot_cpm_instance 1 2 check ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 201.960000} -orientation R0
place_macro -macro_name [ot_cpm_instance 1 3 data ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 298.620000} -orientation MY
place_macro -macro_name [ot_cpm_instance 1 3 check ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 298.620000} -orientation R0
place_macro -macro_name [ot_cpm_instance 1 4 data ot_sram_1r1w_1024x256_m2_r2c2] -location {482.112000 395.280000} -orientation MY
place_macro -macro_name [ot_cpm_instance 1 4 check ot_sram_1r1w_128x256_m1_r2c2] -location {760.536000 395.280000} -orientation R0
