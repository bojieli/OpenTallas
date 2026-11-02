# Source-only future strict PLACE integration pattern, NOT deployed/admitted.
# Caller pins candidate helper fc2afcb2 and native module8c9; loads all real
# libs/ODB/flat rules before this call, then includes ENTIRE original PRE/body/POST.
proc ot_pg_candidate_strict_place_eval {module body} {
  if {![ot_pg_strict_enabled]} {error OT_PG_CANDIDATE_STRICT_ONE_REQUIRED}
  ot_pg_native_birth_begin $module
  set code [catch {
    if {![ot_pg_native_birth_supported global_placement] || ![ot_pg_native_birth_supported buffer_ports]} {
      error OT_PG_CANDIDATE_PLACE_COMMANDS_NOT_ADMITTED
    }
    uplevel 1 $body
  } result options]
  set cleanup_code [catch {
    set receipt [ot_pg_native_birth_end]
    set final_status [ot_native_pg_status]
    if {[dict get $final_status active]} {error OT_PG_CANDIDATE_CALLBACK_STILL_ACTIVE}
  } cleanup cleanup_options]
  if {$code == 1} {
    if {$cleanup_code} {puts stderr "OT_PG_CANDIDATE_CLEANUP_REFUSED $cleanup"}
    return -options $options $result
  }
  if {$cleanup_code == 1} {return -options $cleanup_options $cleanup}
  if {$cleanup_code != 0} {error "OT_PG_CANDIDATE_NONLOCAL_CLEANUP_REFUSED code=$cleanup_code result=$cleanup"}
  if {$code != 0} {error "OT_PG_CANDIDATE_NONLOCAL_BODY_REFUSED code=$code result=$result"}
  return [dict create result $result native $receipt final_status $final_status]
}
