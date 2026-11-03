# PRIVATE observational diagnostic. Use qualified562 helper, never filler candidate.
source /work/native_pg_binding.tcl
if {![ot_pg_strict_enabled]} {error DRT_DIAG_REQUIRES_STRICT_MODE}
if {![info exists ::env(SKIP_DETAILED_ROUTE)] || ![string is boolean -strict $::env(SKIP_DETAILED_ROUTE)] || $::env(SKIP_DETAILED_ROUTE)} {error DRT_DIAG_REQUIRES_ACTUAL_DETAILED_ROUTE}
# Exact proposed PC policy: must be collected from normal recipe before release.
if {![info exists ::env(SKIP_ANTENNA_REPAIR_POST_DRT)] || ![string is boolean -strict $::env(SKIP_ANTENNA_REPAIR_POST_DRT)] || $::env(SKIP_ANTENNA_REPAIR_POST_DRT)} {error DRT_DIAG_REQUIRES_ENABLED_STANDARD_ANTENNA_REPAIR}
if {![info exists ::env(MAX_REPAIR_ANTENNAS_ITER_DRT)] || ![string is integer -strict $::env(MAX_REPAIR_ANTENNAS_ITER_DRT)] || $::env(MAX_REPAIR_ANTENNAS_ITER_DRT) != 5} {error DRT_DIAG_REQUIRES_STANDARD_ANTENNA_MAX5}
foreach flag {SKIP_ANTENNA_REPAIR_POST_DRT MAX_REPAIR_ANTENNAS_ITER_DRT} {
  set value <unset>
  if {[info exists ::env($flag)]} {set value $::env($flag)}
  puts "DRT_DIAG_RESOLVED_POLICY $flag=$value"
}
# PC-specific reviewed PRE, not a generic nonempty-hook allowance.
if {![info exists ::env(PRE_DETAIL_ROUTE_TCL)] || $::env(PRE_DETAIL_ROUTE_TCL) ne "/work/eco_drt_pre.tcl"} {error PC_DRT_EXACT_PRE_REQUIRED}
if {[lindex [exec sha256sum -- /work/eco_drt_pre.tcl] 0] ne "bdda428129a59ba06014d747b1f4caa2a61d8aab4a67697622d4e6b05be53dfd"} {error PC_DRT_PRE_BYTES_CHANGED}
foreach hook {POST_DETAIL_ROUTE_TCL OT_ECO_DRT_PRE_CHAIN} {
  if {[info exists ::env($hook)] && [string trim $::env($hook)] ne ""} {error "PC_DRT_UNREVIEWED_HOOK $hook"}
}
source /work/pg_drt_diag_library_guard.tcl
set ::ot_pg_drt_diag_input_libraries [ot_pg_drt_diag_library_inventory]
proc ot_pg_drt_diag_instances {} {
  set out {}
  foreach inst [[ord::get_db_block] getInsts] {
    lappend out [list [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrigin] [$inst getOrient] [$inst getPlacementStatus] [$inst isDoNotTouch] [$inst getSourceType]]
  }
  return [lsort $out]
}
ot_pg_native_birth_begin /work/nativepgbirth.so
set ::ot_pg_drt_diag_input_instances [ot_pg_drt_diag_instances]
