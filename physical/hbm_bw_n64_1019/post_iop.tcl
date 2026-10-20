# Clock enters W face M4 at the centre of the full-width central std-cell band (y 157.176..216.0).
set ot_bw_clk [[ord::get_db_block] findBTerm clk]
foreach ot_bw_pin [$ot_bw_clk getBPins] { odb::dbBPin_destroy $ot_bw_pin }
place_pin -pin_name clk -layer M4 -location {0 186.624} -force_to_die_boundary
puts "BW_N64_CLOCK: W/M4 y186.624 centre of the core band"
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
