# Correct persisted M5-only GRT state from reused placement/CTS DB.
source /work/core_grt_pre_legacy.tcl
source $::env(PLATFORM_DIR)/fastroute.tcl
set_routing_layers -signal M2-M7 -clock M2-M7
puts "QCORE_ACTUAL_M7_CONFIG signal=M2-M7 clock=M2-M7 adjustment=$::env(ROUTING_LAYER_ADJUSTMENT) existing_data_clock_placement_preserved=1"
