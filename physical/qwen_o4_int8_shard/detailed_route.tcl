set root /tmp/opentallas-qwen-o4-physical-lane
set work /tmp/qwen-o4-shard-route
set platform /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
set macro $root/physical/asap7_memory_macros/ot_rom_8192x266_m8
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {[string match *FAKE* $lib]} { continue }
    read_liberty $lib
}
read_liberty $macro/ot_rom_8192x266_m8_tt.lib
read_db $work/grt.odb
set block [ord::get_db_block]
foreach name {one_ zero_} {
    set net [$block findNet $name]
    if {$net ne "NULL"} { $net setSigType SIGNAL }
}
read_sdc $root/physical/qwen_o4_int8_shard/constraint.sdc
source $platform/setRC.tcl
detailed_route -output_drc $work/drc.rpt
extract_parasitics -ext_model_file $platform/rcx_patterns.rules
set_propagated_clock [all_clocks]
puts "POST_DRT_SETUP"
report_checks -path_delay max
report_wns
puts "POST_DRT_HOLD"
report_checks -path_delay min
report_check_types -max_slew -max_capacitance -max_fanout -violators
write_db $work/final.odb
write_spef $work/final.spef
