set plat /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $plat/lib/NLDM/*RVT_FF*] {read_liberty $f}
set mlib /src/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_ff.lib
read_liberty $mlib
set ::env(OT_PF_MACRO_LIBS) $mlib
read_db /base/4_1_cts.odb
read_sdc /base/4_cts.sdc
source $plat/setRC.tcl
estimate_parasitics -placement
set_propagated_clock [all_clocks]
set ::ot_ce_corner ff
read_sdc $::env(OT_GATE_SIGNOFF_SDC)
foreach delay {max min} {
 set p [lindex [find_timing_paths -path_delay $delay -group_path_count 1 -endpoint_path_count 1 -sort_by_slack] 0]
 puts "DMA_FF $delay slack_ps [get_property $p slack] start [get_full_name [get_property $p startpoint]] end [get_full_name [get_property $p endpoint]]"
 report_checks -path_delay $delay -group_path_count 1 -endpoint_path_count 1 -format full_clock_expanded -digits 3 -fields {slew cap fanout input net}
}
