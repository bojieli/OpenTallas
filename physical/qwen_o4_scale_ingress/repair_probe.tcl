# Diagnostic only: rebuffer the already placed direct ROM cut to separate
# topology/fanout deficits from the analytical macro-to-capture delay.
set root /work
set work /work/out/rom
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set macro $root/physical/asap7_memory_macros/ot_rom_8192x266_m8
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {![string match *FAKE* $lib]} { read_liberty $lib }
}
read_liberty $macro/ot_rom_8192x266_m8_tt.lib
read_db $work/grt.odb
read_sdc $root/physical/qwen_o4_scale_ingress/constraint.sdc
source $platform/setRC.tcl
estimate_parasitics -placement
puts "PRE_REPAIR"
report_checks -path_delay max
repair_design -max_wire_length 100
detailed_placement
estimate_parasitics -placement
puts "POST_BUFFER"
report_checks -path_delay max
repair_timing -setup -max_iterations 5 -max_buffer_percent 10
detailed_placement
set_routing_layers -signal M2-M7 -clock M4-M7
global_route -guide_file $work/repair_route.guide
estimate_parasitics -global_routing
puts "POST_REPAIR_GRT"
report_checks -path_delay max
report_check_types -max_slew -max_capacitance -max_fanout -violators
write_db $work/repair_grt.odb
