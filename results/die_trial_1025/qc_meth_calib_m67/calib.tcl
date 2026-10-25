read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7_tech_1x_201209.lef
read_lef /OpenROAD-flow-scripts/flow/platforms/asap7/lef/asap7sc7p5t_28_R_1x_220121a.lef
foreach f [glob /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/*RVT_TT_nldm*.lib*] { read_liberty $f }
read_def /work/calib.def
source /work/make_tracks.tcl
set_routing_layers -signal M2-M7
set_global_routing_layer_adjustment M2 1.0
set_global_routing_layer_adjustment M3 1.0
set_global_routing_layer_adjustment M4 1.0
set_global_routing_layer_adjustment M5 1.0
global_route -allow_congestion -verbose
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
estimate_parasitics -global_routing -spef_file /work/calib.spef
write_verilog /work/calib.v
report_wire_length -net [get_nets w_*] -global_route -file /work/calib_wl.csv
puts OT_DONE
