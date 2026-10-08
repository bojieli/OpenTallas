# ORFS POST_CTS hook for HALF_PHL=1 (see ph_local.tcl): if the post-CTS repair did not run (SKIP_CTS_REPAIR_TIMING),
# rewire here and legalize; then fail closed unless the phase FF shares the ICG's clock net and sits beside it.
if {[info procs ot_phl_check] eq ""} {source /src/physical/s81_native_bf/margin/ph_local_lib.tcl}
if {!$::ot_phl_done} {
  ot_phl_rewire
  detailed_placement
  estimate_parasitics -placement
}
ot_phl_check post_cts
