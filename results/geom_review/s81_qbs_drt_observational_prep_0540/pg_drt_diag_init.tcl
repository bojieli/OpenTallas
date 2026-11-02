# PRIVATE observational diagnostic. Use qualified562 helper, never filler candidate.
source /work/native_pg_binding.tcl
if {![ot_pg_strict_enabled]} {error DRT_DIAG_REQUIRES_STRICT_MODE}
if {![info exists ::env(SKIP_DETAILED_ROUTE)] || ![string is boolean -strict $::env(SKIP_DETAILED_ROUTE)] || $::env(SKIP_DETAILED_ROUTE)} {error DRT_DIAG_REQUIRES_ACTUAL_DETAILED_ROUTE}
foreach flag {SKIP_ANTENNA_REPAIR_POST_DRT MAX_REPAIR_ANTENNAS_ITER_DRT} {
  set value <unset>
  if {[info exists ::env($flag)]} {set value $::env($flag)}
  puts "DRT_DIAG_RESOLVED_POLICY $flag=$value"
}
foreach hook {PRE_DETAIL_ROUTE_TCL POST_DETAIL_ROUTE_TCL} {
  if {[info exists ::env($hook)] && [string trim $::env($hook)] ne ""} {error "DRT_DIAG_UNREVIEWED_DETAIL_ROUTE_HOOK $hook"}
}
source /work/pg_drt_diag_library_guard.tcl
set ::ot_pg_drt_diag_input_libraries [ot_pg_drt_diag_library_inventory]
# Exact resolved normal antenna policy; no skip/iteration weakening.
if {![info exists ::env(SKIP_ANTENNA_REPAIR_POST_DRT)] || ![string is boolean -strict $::env(SKIP_ANTENNA_REPAIR_POST_DRT)] || $::env(SKIP_ANTENNA_REPAIR_POST_DRT)} {error DRT_DIAG_REQUIRES_ANTENNA_REPAIR_ENABLED}
if {![info exists ::env(MAX_REPAIR_ANTENNAS_ITER_DRT)] || ![string is integer -strict $::env(MAX_REPAIR_ANTENNAS_ITER_DRT)] || $::env(MAX_REPAIR_ANTENNAS_ITER_DRT) != 5} {error DRT_DIAG_REQUIRES_ANTENNA_ITERATIONS_5}
proc ot_pg_drt_diag_instances {} {
  set out {}
  foreach inst [[ord::get_db_block] getInsts] {
    lappend out [list [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrigin] [$inst getOrient] [$inst getPlacementStatus] [$inst isDoNotTouch] [$inst getSourceType]]
  }
  return [lsort $out]
}
ot_pg_native_birth_begin /work/nativepgbirth.so
set ::ot_pg_drt_diag_input_instances [ot_pg_drt_diag_instances]
