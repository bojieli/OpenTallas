# PRIVATE PREP ONLY. Source the immutable562 native_pg_binding helper first.
# Call after loaded-input PG0; write the final saved DB only after this returns.
# Root scope approval and the actual pre-GPL LOOK remain external prerequisites.
proc ot_pg_hroot_private_eval {module body} {
  if {[ot_pg_strict_enabled]} {error HROOT_PRIVATE_GPL_NOT_STRICT_ADMITTED}
  foreach flag {GPL_TIMING_DRIVEN GPL_ROUTABILITY_DRIVEN} {
    if {![info exists ::env($flag)] || $::env($flag) ne "0"} {error "HROOT_REQUIRES_BOTH_MODES_OFF flag=$flag"}
  }
  # Caller body retains exact reviewed -skip_io placement, DPL/source/pose gates
  # and native PGpost. The existing helper owns success/error cleanup.
  append body "\n" {
    set ::ot_pg_hroot_birth_receipt [ot_native_pg_audit]
    foreach field {creates swaps bound} {
      if {[dict get $::ot_pg_hroot_birth_receipt $field] != 0} {
        error "HROOT_UNEXPECTED_NATIVE_BIRTH $::ot_pg_hroot_birth_receipt"
      }
    }
  }
  return [uplevel 1 [list ot_pg_native_birth_eval $module $body]]
}
