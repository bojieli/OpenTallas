if {![info exists ::env(FILL_CELLS)] || [string trim $::env(FILL_CELLS)] eq ""} {error OT_PG_FILL_REQUIRES_EXPLICIT_MASTERS}
# HELD filler adapter; native mechanism qualified, target process release separate.
# PRE begins after loaded DB/libs and before the original full PRE chain.
unset -nocomplain ::ot_pg_fill_post_reached
set ot_pg_fill_code [catch {
  source $::env(SCRIPTS_DIR)/fillcell.native_pg_original.tcl
} ot_pg_fill_result ot_pg_fill_options]
set ot_pg_fill_cleanup_code [catch {
  if {[info commands ot_native_pg_status] ne ""} {
    if {[dict get [ot_native_pg_status] active]} {ot_pg_native_birth_end}
    set ot_pg_fill_final_status [ot_native_pg_status]
    if {[dict get $ot_pg_fill_final_status active]} {error OT_PG_FILL_CALLBACK_STILL_ACTIVE}
    puts "OT_PG_FILL_CALLBACK_FINAL $ot_pg_fill_final_status"
  }
} ot_pg_fill_cleanup ot_pg_fill_cleanup_options]
if {$ot_pg_fill_code == 1} {
  if {$ot_pg_fill_cleanup_code} {puts stderr "OT_PG_FILL_CLEANUP_REFUSED $ot_pg_fill_cleanup"}
  return -options $ot_pg_fill_options $ot_pg_fill_result
}
if {$ot_pg_fill_cleanup_code == 1} {return -options $ot_pg_fill_cleanup_options $ot_pg_fill_cleanup}
if {$ot_pg_fill_cleanup_code != 0} {error "OT_PG_FILL_NONLOCAL_CLEANUP_REFUSED code=$ot_pg_fill_cleanup_code result=$ot_pg_fill_cleanup"}
if {$ot_pg_fill_code != 0} {error "OT_PG_FILL_NONLOCAL_BODY_REFUSED code=$ot_pg_fill_code result=$ot_pg_fill_result"}
if {![info exists ::ot_pg_fill_post_reached] || !$::ot_pg_fill_post_reached} {error OT_PG_FILL_FULL_POST_NOT_REACHED}
