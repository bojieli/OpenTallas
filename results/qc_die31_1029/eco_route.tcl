# DIE-QC-31 c1 ECO route of RR nets only (same GRT/DRT settings as pilot_clip run.tcl)
set P /OpenROAD-flow-scripts/flow/platforms/asap7
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_db /o/eco_in.odb
source $P/openRoad/make_tracks.tcl
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
foreach L {M2 M3 M4 M5 M6 M7} { set_global_routing_layer_adjustment $L 0.99 }
global_route -congestion_iterations 50 -verbose
write_guides /o/eco.guide
detailed_route -output_drc /o/eco_drc.rpt -verbose 1
write_def /o/eco.def
puts "OT_ECO_DONE"
