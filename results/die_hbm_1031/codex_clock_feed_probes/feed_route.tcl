set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_TT_nldm*.lib*] {read_liberty $f}
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
create_clock -name core -period 833.0 [get_ports drive]
set_input_transition 40 [get_ports drive]
set_load 3.0 [get_ports -quiet mesh_root]
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
foreach L {M2 M3 M4 M5 M6 M7} {set_global_routing_layer_adjustment $L 0.99}
create_ndr -name CK2W2S -width {M8 0.08 M9 0.08} -spacing {M8 0.32 M9 0.32}
foreach n [get_nets {feed bridge}] {assign_ndr -ndr CK2W2S -net [get_full_name $n]}
global_route -congestion_iterations 50 -allow_congestion
write_guides /o/route.guide
detailed_route -output_drc /o/drc.rpt -droute_end_iter 20 -verbose 1
write_db /o/route.odb
write_def /o/route.def
source $P/setRC.tcl
define_process_corner -ext_model_index 0 X
set ot_tech [ord::get_db_tech]
foreach {l r} {M1 0.563166 M2 0.534825 M3 0.563166 M4 0.432876 M5 0.455842 M6 0.380144 M7 0.400304 M8 0.27935 M9 0.29417} {[$ot_tech findLayer $l] setResistance $r}
extract_parasitics -ext_model_file $P/rcx_patterns.rules -lef_res
write_spef /o/route.spef
puts OT_FEED_ROUTE_DONE
