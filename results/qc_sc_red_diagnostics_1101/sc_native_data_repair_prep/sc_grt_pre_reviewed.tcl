# Honest fixed-clock PLACE input already loaded by native load_design.
source /work/sc_native_clock_inventory.tcl
source /work/sc_guard.tcl
set ::sc_repair_public_terms [sc_terms]
source /work/clk_freeze.tcl
file mkdir $::env(RESULTS_DIR)/sc_clock_freeze
ot_clk_freeze $::env(RESULTS_DIR)/sc_clock_freeze
source /work/sc_ff_master_preserve.tcl
source /work/grt_pre_core.tcl
# Exact prior diagnostic deck; clocks stay native routing-eligible.
set_routing_layers -signal M2-M5
set_routing_layers -clock M4-M5
set_global_routing_layer_adjustment M2-M5 0.25
