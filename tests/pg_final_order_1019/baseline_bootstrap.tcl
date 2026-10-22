# Strict opt-in bootstrap in each staged OpenROAD process.
if {[info exists ::env(OT_PG_STRICT)] && $::env(OT_PG_STRICT) eq "1"} {
  set ot_pg_helper [file join [file dirname [info script]] native_pg_binding.tcl]
  if {[info exists ::env(OT_PG_HELPER)]} {set ot_pg_helper $::env(OT_PG_HELPER)} elseif {![file exists $ot_pg_helper]} {set ot_pg_helper /src/physical/common_flow/native_pg_binding.tcl}
  source $ot_pg_helper
  ot_pg_install_final_write_guard
}
