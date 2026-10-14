define_corners WC BC

foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] { read_liberty -corner WC $l }
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] {read_liberty -corner BC $l}
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
read_spef -corner WC /base/6_final.spef
read_spef -corner BC /base/6_final.spef
set_propagated_clock [all_clocks]

puts "OT_FF_INTERNAL_HOLD"
report_checks -from [all_registers -clock_pins] -to [all_registers -data_pins] -path_delay min -group_path_count 4 -format full_clock_expanded
set block [ord::get_db_block]
foreach inst [$block getInsts] {
 if {![[$inst getMaster] isBlock]} continue
 puts "OT_MACRO [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [[$inst getBBox] xMin] [[$inst getBBox] yMin] [[$inst getBBox] xMax] [[$inst getBBox] yMax]"
}
foreach nn {net9290 net19914 net9766 net9758 net19833} {
 set net [$block findNet $nn]
 puts "OT_DRC_NET $nn"
 foreach it [$net getITerms] {
 puts "OT_DRC_ITERM [$it getName] [[$it getMTerm] getIoType] [$it getAvgXY]"
 }
}
exit
