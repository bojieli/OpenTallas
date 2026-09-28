set arm $::env(QWEN_SCALE_ARM)
set root /work
set work /work/out/$arm
set platform /OpenROAD-flow-scripts/flow/platforms/asap7
set macro $root/physical/asap7_memory_macros/ot_rom_8192x266_m8
read_lef $platform/lef/asap7_tech_1x_201209.lef
read_lef $platform/lef/asap7sc7p5t_28_R_1x_220121a.lef
if {$arm eq "rom"} { read_lef $macro/ot_rom_8192x266_m8.lef }
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {![string match *FAKE* $lib]} { read_liberty $lib }
}
if {$arm eq "rom"} { read_liberty $macro/ot_rom_8192x266_m8_tt.lib }
read_verilog $work/mapped.v
link_design ot_qwen_o4_scale_ingress_probe
initialize_floorplan -die_area {0 0 240 240} -core_area {15 15 225 225} -site asap7sc7p5t
source $platform/openRoad/make_tracks.tcl
source $platform/setRC.tcl
if {$arm eq "rom"} { place_macro -macro_name g_rom_u_scale_rom -location {35 60} }
repair_tie_fanout TIEHIx1_ASAP7_75t_R/H
repair_tie_fanout TIELOx1_ASAP7_75t_R/L
read_sdc $root/physical/qwen_o4_scale_ingress/constraint.sdc
place_pins -hor_layers M4 -ver_layers M5
global_placement -density 0.45 -bin_grid_count 128
detailed_placement
estimate_parasitics -placement
puts "POST_PLACE_SETUP"
report_checks -path_delay max
clock_tree_synthesis -root_buf BUFx2_ASAP7_75t_R
detailed_placement
estimate_parasitics -placement
puts "POST_CTS_SETUP"
report_checks -path_delay max
puts "POST_CTS_HOLD"
report_checks -path_delay min
set_routing_layers -signal M2-M7 -clock M4-M7
global_route -guide_file $work/route.guide
estimate_parasitics -global_routing
puts "POST_GRT_SETUP"
report_checks -path_delay max
puts "POST_GRT_HOLD"
report_checks -path_delay min
write_db $work/grt.odb
