# Diagnostic direct OpenROAD route for the source-pinned, mapped INT8 block.
# This is independent of the project's ORFS sign-off flow.
set platform /home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7
set work /tmp/qwen-o4-int8-arith-sta
read_lef $platform/lef/asap7_tech_1x_201209.lef
read_lef $platform/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach lib [glob $platform/lib/NLDM/*RVT_TT_nldm*] {
    if {[string match *FAKE* $lib]} { continue }
    read_liberty $lib
}
read_verilog $work/mapped.v
link_design ot_hdc_qwen_int8_arith
initialize_floorplan -die_area {0 0 70 70} -core_area {5 5 65 65} -site asap7sc7p5t
source $platform/openRoad/make_tracks.tcl
source $platform/setRC.tcl
repair_tie_fanout TIEHIx1_ASAP7_75t_R/H
repair_tie_fanout TIELOx1_ASAP7_75t_R/L
read_sdc $work/constraint.sdc
place_pins -hor_layers M4 -ver_layers M5
global_placement -density 0.55
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
global_route -guide_file /tmp/qwen-o4-int8-arith.guide
estimate_parasitics -global_routing
puts "POST_GRT_SETUP"
report_checks -path_delay max
puts "POST_GRT_HOLD"
report_checks -path_delay min
write_db /tmp/qwen-o4-int8-arith-grt.odb
