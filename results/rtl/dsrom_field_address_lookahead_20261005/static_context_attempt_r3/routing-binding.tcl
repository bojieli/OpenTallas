read_db /probe/work/orfs/results/asap7/opentallas_ot_v41_static_provider_context_asap7_epicurus_static_context_r1/base/1_synth.odb
initialize_floorplan -die_area {0 0 207.36 108} -core_area {2.16 2.16 205.2 107.73} -site asap7sc7p5t
source /OpenROAD-flow-scripts/flow/platforms/asap7/openRoad/make_tracks.tcl
set_routing_layers -signal M2-M8
puts "SIGNAL_UMBRELLA8"
set_routing_layers -clock M7-M8
puts "CLOCK8"
set_routing_layers -signal M2-M7
puts "DATA7_CLOCK8_PASS"
exit
