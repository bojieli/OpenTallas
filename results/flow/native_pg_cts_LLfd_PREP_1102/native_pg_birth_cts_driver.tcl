# PRIVATE CTS canary, ordinary do-4_1_cts environment. No strict CTS admission.
# PRE begins after loaded DB/libs and before the original full PRE chain.
unset -nocomplain ::ot_pg_cts_post_reached
set ot_pg_cts_code [catch {
  source $::env(SCRIPTS_DIR)/cts.native_pg_original.tcl
} ot_pg_cts_result ot_pg_cts_options]
set ot_pg_cts_cleanup_code [catch {
  if {[info commands ot_native_pg_status] ne ""} {
    if {[dict get [ot_native_pg_status] active]} {ot_pg_native_birth_end}
    set ot_pg_cts_final_status [ot_native_pg_status]
    if {[dict get $ot_pg_cts_final_status active]} {error OT_PG_CTS_CALLBACK_STILL_ACTIVE}
    puts "OT_PG_CTS_CALLBACK_FINAL $ot_pg_cts_final_status"
  }
} ot_pg_cts_cleanup ot_pg_cts_cleanup_options]
if {$ot_pg_cts_code == 1} {
  if {$ot_pg_cts_cleanup_code} {puts stderr "OT_PG_CTS_CLEANUP_REFUSED $ot_pg_cts_cleanup"}
  return -options $ot_pg_cts_options $ot_pg_cts_result
}
if {$ot_pg_cts_cleanup_code == 1} {return -options $ot_pg_cts_cleanup_options $ot_pg_cts_cleanup}
if {$ot_pg_cts_cleanup_code != 0} {error "OT_PG_CTS_NONLOCAL_CLEANUP_REFUSED code=$ot_pg_cts_cleanup_code result=$ot_pg_cts_cleanup"}
if {$ot_pg_cts_code != 0} {error "OT_PG_CTS_NONLOCAL_BODY_REFUSED code=$ot_pg_cts_code result=$ot_pg_cts_result"}
if {![info exists ::ot_pg_cts_post_reached] || !$::ot_pg_cts_post_reached} {error OT_PG_CTS_FULL_POST_NOT_REACHED}
