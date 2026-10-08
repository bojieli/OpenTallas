# ORFS POST_CTS hook for cg_local.tcl: rewire here if the post-CTS repair did not run, then report (fails closed).
if {[info procs ot_cgl_check] eq ""} {error "BF_CGL: PRE_CTS cg_local.tcl not loaded"}
if {!$::ot_cgl_done} { ot_cgl_rewire; detailed_placement; estimate_parasitics -placement }
ot_cgl_check post_cts
