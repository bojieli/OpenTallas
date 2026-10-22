set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach pat {AO INVBUF OA SIMPLE SEQ} {
 foreach f [glob $P/lib/NLDM/*${pat}_RVT_TT_nldm*] {if {![string match *FAKE* $f]} {read_liberty $f}}
}
set v $::env(COUPON_VARIANT)
set O /coupon/$v/orfs/results/asap7/fc_coupon/base
file mkdir $O
read_verilog /coupon/$v/input.v
link_design fc_coupon
initialize_floorplan -die_area {0 0 40 40} -core_area {5.4 5.4 34.56 34.56} -site asap7sc7p5t
source $P/openRoad/make_tracks.tcl
place_inst -name b0 -location {8.1 20.52} -orientation R0 -status PLACED
if {$v eq "chain"} {
 place_inst -name inv -location {15.12 20.52} -orientation R0 -status PLACED
 place_inst -name b1 -location {22.14 20.52} -orientation R0 -status PLACED
}
place_inst -name ff -location {16.2 10.26} -orientation R0 -status PLACED
place_pin -pin_name clk_in -layer M4 -location {0 20.508} -force_to_die_boundary
place_pin -pin_name d -layer M4 -location {0 10.284} -force_to_die_boundary
place_pin -pin_name clk_out -layer M4 -location {40 20.508} -force_to_die_boundary
place_pin -pin_name q -layer M4 -location {40 10.284} -force_to_die_boundary
add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VDD$} -power
add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VSS$} -ground
global_connect
read_sdc /coupon/$v/input.sdc
source $P/setRC.tcl
set_routing_layers -signal M2-M6 -clock M2-M6
global_route
# Native routed coupon; no closure/sign-off qualification is inferred.
detailed_route -output_drc /coupon/$v/drc.rpt
set rules $P/rcx_patterns.rules
if {![file exists $rules]} {error "Native extraction rules missing: $rules"}
extract_parasitics -ext_model_file $rules
write_spef $O/6_final.spef
write_db $O/6_final.odb
write_verilog $O/6_final.v
write_sdc $O/6_final.sdc
puts "OT_COUPON_WS [sta::worst_slack_cmd max] [sta::worst_slack_cmd min]"
puts OT_COUPON_DONE
exit
