# PRIVATE observational DRT diagnostic; no generic birth admission.
# Run this driver with the normal GRT make target's loaded environment.
# PRE installs after load_design; this outer body also cleans up failed hooks.
set ot_pg_drt_code [catch {
  source $::env(SCRIPTS_DIR)/detail_route.native_pg_original.tcl
} ot_pg_drt_result ot_pg_drt_options]
set ot_pg_drt_cleanup_code 0
if {[info commands ot_native_pg_status] ne ""} {
  set ot_pg_drt_cleanup_code [catch {
    if {[dict get [ot_native_pg_status] active]} {ot_pg_native_birth_end}
  } ot_pg_drt_cleanup ot_pg_drt_cleanup_options]
}
if {$ot_pg_drt_code} {
  if {$ot_pg_drt_cleanup_code} {puts stderr "OT_PG_DRT_CLEANUP_REFUSED $ot_pg_drt_cleanup"}
  return -options $ot_pg_drt_options $ot_pg_drt_result
}
if {$ot_pg_drt_cleanup_code} {
  return -options $ot_pg_drt_cleanup_options $ot_pg_drt_cleanup
}
