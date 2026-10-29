# Current fresh-kit successor: open layers BEFORE applying all-layer reductions.
source /work/core_grt_pre_legacy.tcl
set_routing_layers -signal M2-M7 -clock M2-M7
source $::env(PLATFORM_DIR)/fastroute.tcl
set_global_routing_layer_adjustment M2-M7 $::env(ROUTING_LAYER_ADJUSTMENT)
puts "QCORE_ACTUAL_M7_CONFIG signal=M2-M7 clock=M2-M7 adjustment=$::env(ROUTING_LAYER_ADJUSTMENT) existing_data_clock_placement_preserved=1"
