# Own failed final5_1 continuation; original4_cts SDC keeps proper TT/FF mode identity.
source $::env(SCRIPTS_DIR)/load.tcl
load_design 5_1_grt.odb 4_cts.sdc
set_propagated_clock [get_clocks clk]
set_routing_layers -signal M2-M5 -clock M2-M5
source /work/core_final_repair.tcl
write_db $::env(RESULTS_DIR)/5_1_grt.odb
write_sdc -no_timestamp $::env(RESULTS_DIR)/5_1_grt.sdc
puts "OT_CORE_FINAL_RESUME_DONE: fresh actual policy still required"
