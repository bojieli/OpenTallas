set arm $::env(QWEN_SCALE_ARM)
set root /work
set work /work/out/${arm}_reg
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set macro $root/physical/asap7_memory_macros/ot_rom_8192x266_m8
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {![string match *FAKE* $lib]} { read_liberty $lib }
}
if {$arm eq "rom"} { read_liberty $macro/ot_rom_8192x266_m8_tt.lib }
read_db $work/grt.odb
read_sdc $root/physical/qwen_o4_scale_ingress/constraint.sdc
source $platform/setRC.tcl
set_propagated_clock [all_clocks]
set_routing_layers -signal M2-M7 -clock M4-M7
global_route -guide_file $work/sta_route.guide
estimate_parasitics -global_routing
if {$arm eq "rom"} {
    puts "ROM_SOURCE_TO_RAW_CAPTURE_GRT"
    report_checks -from [get_pins g_rom_u_scale_rom/rd_out*] -path_delay max
    puts "ROM_SOURCE_TO_RAW_CAPTURE_HOLD_GRT"
    report_checks -from [get_pins g_rom_u_scale_rom/rd_out*] -path_delay min
} else {
    puts "HBM_SOURCE_TO_RAW_CAPTURE_GRT"
    report_checks -from [get_ports hbm_scale_word*] -path_delay max
    puts "HBM_SOURCE_TO_RAW_CAPTURE_HOLD_GRT"
    report_checks -from [get_ports hbm_scale_word*] -path_delay min
}
puts "SCALE_GROUP_ENABLE_GRT"
report_checks -from [get_ports scale_group_re] -path_delay max
puts "SCALE_GROUP_ENABLE_HOLD_GRT"
report_checks -from [get_ports scale_group_re] -path_delay min
puts "WORST_CORE_SETUP_GRT"
report_checks -path_delay max -group_path_count 1
puts "WORST_CORE_HOLD_GRT"
report_checks -path_delay min -group_path_count 1
