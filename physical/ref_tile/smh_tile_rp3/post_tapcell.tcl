# ref_tile: exact abutment pins first (IO_CONSTRAINTS is otherwise sourced only at 3_2_place_iop, where it
# re-applies the same placement), then the spec's POST_TAPCELL hook (boundary flops FIRM at their pins)
source /src/physical/ref_tile_specs/smh/smh_tile_rp3_pins.tcl
source /src/physical/ref_tile_specs/smh/smh_tile_rp3_strap_regions.tcl
# then unplace the pins again: 3_2_place_iop re-sources io_tcl, and place_pins aborts in createIOGroup when
# a pin group's (clk / reset) ports are already placed (smh_pt_e_ref_p40s gate, signal 6)
# signal ports only: POWER/GROUND BTerm pins (made by pdngen at 2_4) are never re-created by io_tcl or
# place_pins; a pinless VDD/VSS BTerm makes AntennaChecker::designIsPlaced() false -> ANT-0008 at 5_1_grt
foreach bt [[ord::get_db_block] getBTerms] { if {[$bt getSigType] in {POWER GROUND}} continue; foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }
