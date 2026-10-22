# Strict opt-in PRE_FINAL_REPORT entry, before ORFS final_connect global_connect.
if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
  set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_pg_helper
  # Refuse a stale binding before canonical global_connect can repair it and
  # hide a change made after extraction. Keep the write guard as a second check.
  ot_pg_final_guard
  ot_pg_install_final_write_guard
}
