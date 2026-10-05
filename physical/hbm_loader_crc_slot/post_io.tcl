# Apply Kant's exact 1410 actual facade pins after the ordinary IO-placement
# stage, then rewrite that same stage DB. No generated timing exception.
source /src/physical/hbm_loader_crc_slot/pins.tcl
set lp_count 0
set lp_supply 0
foreach lp_term [[ord::get_db_block] getBTerms] {
    # ORFS adds VDD/VSS BTerms. Kant's 1410-pin manifest is the signal
    # facade; supply BTerms are retained and are outside that manifest.
    if {[$lp_term getSigType] in {POWER GROUND}} {
        incr lp_supply
    } else {
        incr lp_count
    }
}
if {$lp_count != 1410} {error "wide ND1 loader signal pin census $lp_count !=1410 (supply $lp_supply)"}
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
puts "LOADER_KANT_PINS $lp_count signals supply=$lp_supply fixed corrected square slot"
