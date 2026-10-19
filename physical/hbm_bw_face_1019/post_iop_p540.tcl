# L2H-BW face_p540: clock enters the W face on M4 at the centre of the full-width central std-cell band (y 106.368).
set ot_bw_clk [[ord::get_db_block] findBTerm clk]
foreach ot_bw_pin [$ot_bw_clk getBPins] { odb::dbBPin_destroy $ot_bw_pin }
place_pin -pin_name clk -layer M4 -location {0 106.368} -force_to_die_boundary
puts "BW_FACE_CLOCK: W/M4 y106.368 centre of the core band"
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
