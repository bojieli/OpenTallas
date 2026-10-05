set arm $::env(QWEN_SCALE_ARM)
set root /work
set work /work/out/$arm
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set macro $root/physical/asap7_memory_macros/ot_rom_8192x266_m8
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {![string match *FAKE* $lib]} { read_liberty $lib }
}
if {$arm eq "rom"} { read_liberty $macro/ot_rom_8192x266_m8_tt.lib }
read_db $work/grt.odb
read_sdc $root/physical/qwen_o4_scale_ingress/constraint.sdc
source $platform/setRC.tcl
# OpenROAD does not persist the GRT estimator state in the ODB. This source
# breakdown uses placement parasitics on the same placed database; the main
# place_route.log carries the actual GRT timing result.
estimate_parasitics -placement
if {$arm eq "rom"} {
    puts "ROM_SOURCE_TO_CAPTURE"
    report_checks -from [get_pins g_rom_u_scale_rom/rd_out*] -path_delay max
} else {
    puts "HBM_SOURCE_TO_CAPTURE"
    report_checks -from [get_ports hbm_scale_word*] -path_delay max
}
puts "COMPLETED_SUM_TO_SCALE_LANE"
report_checks -from [get_ports completed_sum*] -path_delay max
puts "SCALE_GROUP_ENABLE"
report_checks -from [get_ports scale_group_re] -path_delay max
