# HELD PREP: filler process qualification pending root-reviewed native vehicle.
if {![info exists ::env(FILL_CELLS)] || [string trim $::env(FILL_CELLS)] eq ""} {error OT_PG_FILL_REQUIRES_EXPLICIT_MASTERS}
# Run this driver with the normal GRT make target's loaded environment.
# PRE installs after load_design; this outer body also cleans up failed hooks.
set ot_pg_fill_code [catch {
  source $::env(SCRIPTS_DIR)/fillcell.native_pg_original.tcl
} ot_pg_fill_result ot_pg_fill_options]
set ot_pg_fill_cleanup_code 0
if {[info commands ot_native_pg_status] ne ""} {
  set ot_pg_fill_cleanup_code [catch {
    if {[dict get [ot_native_pg_status] active]} {ot_pg_native_birth_end}
  } ot_pg_fill_cleanup ot_pg_fill_cleanup_options]
}
if {$ot_pg_fill_code} {
  if {$ot_pg_fill_cleanup_code} {puts stderr "OT_PG_FILL_CLEANUP_REFUSED $ot_pg_fill_cleanup"}
  return -options $ot_pg_fill_options $ot_pg_fill_result
}
if {$ot_pg_fill_cleanup_code} {
  return -options $ot_pg_fill_cleanup_options $ot_pg_fill_cleanup
}
