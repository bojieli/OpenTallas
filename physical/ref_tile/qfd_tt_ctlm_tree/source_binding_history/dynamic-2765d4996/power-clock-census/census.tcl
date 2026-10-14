define_corners WC BC

foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT*] { read_liberty -corner WC $l }
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_tt.lib
read_liberty -corner WC /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_tt.lib
foreach l [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_FF*] {read_liberty -corner BC $l}
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2_ff.lib
read_liberty -corner BC /src/physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_db /base/6_final.odb
read_sdc /base/6_final.sdc
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]


set counts [dict create]
foreach i [[ord::get_db_block] getInsts] {
 set m [[$i getMaster] getName]
 if {![string match *DFF* $m]} continue
 set n [$i getName]
 set top [lindex [split $n .] 0]
 dict incr counts $top
}
dict for {n v} $counts {puts "OT_HEAD_FF $n $v"}
exit
