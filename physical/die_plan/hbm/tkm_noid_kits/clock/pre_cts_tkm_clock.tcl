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
