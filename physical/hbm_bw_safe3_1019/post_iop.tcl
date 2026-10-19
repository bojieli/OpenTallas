# Reposition only the clock; retain every other pin's balanced face plan.
set ot_bw_clk [[ord::get_db_block] findBTerm clk]
foreach ot_bw_pin [$ot_bw_clk getBPins] { odb::dbBPin_destroy $ot_bw_pin }
place_pin -pin_name clk -layer M4 -location {0 278.208} -force_to_die_boundary
puts "BW_SAFE3_CLOCK: W/M4 y278.208 beside the core register band"
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
