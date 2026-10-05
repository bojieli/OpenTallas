set root /tmp/opentallas-qwen-o4-physical-lane
set work /tmp/qwen-o4-shard-route
set platform /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] { if {![string match *FAKE* $lib]} { read_liberty $lib } }
read_liberty $root/physical/asap7_memory_macros/ot_rom_8192x266_m8/ot_rom_8192x266_m8_tt.lib
read_db $work/grt.odb
read_sdc $root/physical/qwen_o4_int8_shard/constraint.sdc
source $platform/setRC.tcl
estimate_parasitics -global_routing
set pins [get_pins -hierarchical u_weight_rom/rd_out*]
puts "ROM_OUT_PINS [llength $pins]"
report_checks -from $pins -path_delay max
