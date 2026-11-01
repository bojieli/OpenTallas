set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_TT_nldm*.lib*] {read_liberty $f}
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
set block [ord::get_db_block]
set mesh [$block findNet ck_mesh]
puts "CONTACT_BEFORE special=[$mesh isSpecial] swires=[llength [$mesh getSWires]] regularwire=[$mesh getWire]"
$mesh clearSpecial
foreach it [$mesh getITerms] {$it clearSpecial}
puts "CONTACT_AFTER special=[$mesh isSpecial] swires=[llength [$mesh getSWires]]"
if {[$mesh isSpecial]} {error {mesh still special: cannot route actual output contacts}}
foreach p {drive0 drive1} {create_clock -name $p -period 833.0 [get_ports $p]}
set_input_transition 40 [get_ports {drive0 drive1}]
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
foreach L {M2 M3 M4 M5 M6 M7} {set_global_routing_layer_adjustment $L 0.99}
source /o/ndr.tcl
foreach n [get_nets *] {assign_ndr -ndr CONTACT -net [get_full_name $n]}
global_route -congestion_iterations 50 -allow_congestion
write_guides /o/route.guide
foreach n [get_nets *] {assign_ndr -ndr CONTACT -net [get_full_name $n]}
detailed_route -output_drc /o/drc.rpt -droute_end_iter 20 -verbose 1
write_db /o/route.odb
write_def /o/route.def
puts "CONTACT_ROUTED swires=[llength [$mesh getSWires]] regularwire=[$mesh getWire]"
if {[$mesh getWire] eq "NULL"} {error {no actual regular pin-to-mesh wire}}
source $P/setRC.tcl
define_process_corner -ext_model_index 0 X
source /o/rcx.tcl
write_spef /o/route.spef
puts OT_MESH_CONTACT_ROUTE_DONE
