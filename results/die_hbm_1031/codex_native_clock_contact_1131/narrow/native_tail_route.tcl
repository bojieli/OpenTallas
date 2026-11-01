set P /OpenROAD-flow-scripts/flow/platforms/asap7
foreach f [glob $P/lib/NLDM/*RVT_TT_nldm*.lib*] {read_liberty $f}
read_liberty /o/ot_hbm_idx_tail_native_tt.lib
read_lef $P/lef/asap7_tech_1x_201209.lef
read_lef $P/lef/asap7sc7p5t_28_R_1x_220121a.lef
read_lef /o/ot_hbm_idx_tail_native.lef
read_def /o/pilot.def
source $P/openRoad/make_tracks.tcl
create_clock -name core -period 833 [get_ports drive]
set_input_transition 40 [get_ports drive]
set_clock_uncertainty -setup 0 [get_clocks core]
set_clock_uncertainty -hold 25 [get_clocks core]
set_routing_layers -signal M2-M9 -clock M8-M9
set_global_routing_layer_adjustment M8 0.4
set_global_routing_layer_adjustment M9 0.4
foreach layer {M2 M3 M4 M5 M6 M7} {set_global_routing_layer_adjustment $layer 0.99}
source /o/ndr.tcl
assign_ndr -ndr NATIVE_CLOCK -net native_clock
global_route -congestion_iterations 50 -allow_congestion
write_guides /o/route.guide
assign_ndr -ndr NATIVE_CLOCK -net native_clock
detailed_route -output_drc /o/drc.rpt -droute_end_iter 20 -verbose 1
write_db /o/route.odb
write_def /o/route.def
source $P/setRC.tcl
define_process_corner -ext_model_index 0 X
source /o/rcx.tcl
write_spef /o/route.spef
puts OT_NATIVE_CLK_PIN_PHYSICALLY_ROUTED
