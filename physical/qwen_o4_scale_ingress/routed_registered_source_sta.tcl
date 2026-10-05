set arm $::env(QWEN_SCALE_ARM)
set root /work
set work /work/out/${arm}_reg
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set macro $root/physical/asap7_memory_macros/ot_rom_8192x266_m8
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {![string match *FAKE* $lib]} { read_liberty $lib }
}
if {$arm eq "rom"} { read_liberty $macro/ot_rom_8192x266_m8_tt.lib }
read_db $work/final.odb
read_sdc $root/physical/qwen_o4_scale_ingress/constraint.sdc
source $platform/setRC.tcl
read_spef $work/final.spef
set_propagated_clock [all_clocks]
if {$arm eq "rom"} {
    puts "ROM_SOURCE_TO_RAW_CAPTURE_ROUTED"
    report_checks -from [get_pins g_rom_u_scale_rom/rd_out*] -path_delay max
    puts "ROM_SOURCE_TO_RAW_CAPTURE_HOLD_ROUTED"
    report_checks -from [get_pins g_rom_u_scale_rom/rd_out*] -path_delay min
} else {
    puts "HBM_SOURCE_TO_RAW_CAPTURE_ROUTED"
    report_checks -from [get_ports hbm_scale_word*] -path_delay max
    puts "HBM_SOURCE_TO_RAW_CAPTURE_HOLD_ROUTED"
    report_checks -from [get_ports hbm_scale_word*] -path_delay min
}
puts "SCALE_GROUP_ENABLE_ROUTED"
report_checks -from [get_ports scale_group_re] -path_delay max
puts "SCALE_GROUP_ENABLE_HOLD_ROUTED"
report_checks -from [get_ports scale_group_re] -path_delay min
