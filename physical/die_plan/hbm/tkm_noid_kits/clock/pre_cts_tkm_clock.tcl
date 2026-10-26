# Fail before touching the clock graph if the explicit tile clock contract is missing.
if {![info exists ::env(OT_DTAP_PORT)] || $::env(OT_DTAP_PORT) ne "tile_clk"} {
  error "TKM clock stage requires OT_DTAP_PORT=tile_clk"
}
set ot_tkm_clock_port [[ord::get_db_block] findBTerm $::env(OT_DTAP_PORT)]
if {$ot_tkm_clock_port eq "NULL" || $ot_tkm_clock_port eq ""} {
  error "TKM clock stage: tile_clk BTerm is absent"
}
source /work/core_density_taps.tcl
source /work/shallow_clock.tcl
ot_dtsh::setup $::dt_blk $::dt_taps $::dt_root $::dt_cell
source /work/hbm_clock_entry.tcl
ot_hbmentry::setup $::dt_blk $::dt_port 20
# Hold every existing placement across CTS legalisation: ORFS cts.tcl runs
# detailed_placement after clock_tree_synthesis, and a PLACED neighbour would be
# displaced to make room for new CTS buffers, which ot_dtsh::audit rejects by
# contract. FIRM existing cells make DPL legalise only the new clock cells.
# The list is restored to PLACED in POST_CTS after the audit passes.
set ::ot_tkm_cts_firm {}
foreach ot_tkm_name [dict keys $::ot_dtsh::original] {
  set ot_tkm_inst [$::dt_blk findInst $ot_tkm_name]
  if {$ot_tkm_inst eq "NULL" || $ot_tkm_inst eq ""} { error "TKM CTS hold: existing cell $ot_tkm_name vanished before CTS" }
  if {[$ot_tkm_inst getPlacementStatus] ne "PLACED"} continue
  $ot_tkm_inst setPlacementStatus FIRM
  lappend ::ot_tkm_cts_firm $ot_tkm_name
}
puts "OT_TKM_CTS_HOLD FIRM [llength $::ot_tkm_cts_firm] of [dict size $::ot_dtsh::original] existing placements for CTS legalisation"
