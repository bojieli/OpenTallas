# Apply Kant's exact 1410 actual facade pins after the ordinary IO-placement
# stage, then rewrite that same stage DB. No generated timing exception.
source /src/physical/hbm_loader_crc_slot/pins.tcl
set lp_count [llength [[ord::get_db_block] getBTerms]]
if {$lp_count != 1410} {error "wide ND1 loader facade physical pin census !=1410"}
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
puts "LOADER_KANT_PINS 1410 fixed corrected square slot"
