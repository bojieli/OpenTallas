# ref_tile: re-apply the exact abutment pin plan after place_pins (IO_CONSTRAINTS is sourced only at
# 2_1_floorplan; the POST_TAPCELL hook unplaced the ports so place_pins could run) and save the stage result
set ot_blk [ord::get_db_block]
foreach bt [$ot_blk getBTerms] { if {[$bt getSigType] in {POWER GROUND}} continue; foreach bp [$bt getBPins] { odb::dbBPin_destroy $bp } }
source /src/physical/ref_tile_specs/smh/smh_tile_eg_cpt_pins.tcl
set ot_n 0; set ot_miss {}
foreach bt [$ot_blk getBTerms] {
  if {[$bt getSigType] in {POWER GROUND}} continue
  if {[llength [$bt getBPins]] == 0} { lappend ot_miss [$bt getName] } else { incr ot_n }
}
if {[llength $ot_miss]} { error "REF_TILE exact pin plan: [llength $ot_miss] ports left unplaced ([lrange $ot_miss 0 4])" }
foreach bt [$ot_blk getBTerms] { if {[$bt getSigType] in {POWER GROUND} && [llength [$bt getBPins]] == 0} { error "REF_TILE power port [$bt getName] lost its pdn pin (ANT-0008 at grt)" } }
puts "REF_TILE exact pin plan re-applied after place_pins: $ot_n ports"
orfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb
write_pin_placement $::env(RESULTS_DIR)/3_2_place_iop.tcl
