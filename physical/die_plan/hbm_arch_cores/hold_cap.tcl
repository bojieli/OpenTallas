# ELEM-HBM 10-24 (PRE_GLOBAL_ROUTE hook): the CP1-R10 kit IO standard (input min delay -insertion_tol vs the IO virtual
# clock at the plan insertion) asks every pin-registered input for ~45-90 ps of hold delay; on 4-6k-input cores that
# exceeds ORFS repair_timing's default 20 % buffer cap (RSZ-0060).  Raise the tool cap only (OT_MAX_BUFFER_PERCENT,
# default 100); constraints, margins and corners are unchanged.
# HBM-ELEM 10-24: + an iteration cap (OT_MAX_ITERATIONS, default 4000).  54 idx_score_quarter routes looped for hours
# in the GRT hold repair on ONE endpoint (WNS / TNS flat for >3000 iterations, 2 buffers added per 10 iterations): the
# cap ends the loop so the run reaches route + signoff, which reports the residual honestly (FF hold STA decides).
# source_step_tcl sources this inside a proc: keep the value in a namespace variable.
set ::ot_mbp [expr {[info exists ::env(OT_MAX_BUFFER_PERCENT)] ? $::env(OT_MAX_BUFFER_PERCENT) : 100}]
set ::ot_mit [expr {[info exists ::env(OT_MAX_ITERATIONS)] ? $::env(OT_MAX_ITERATIONS) : 4000}]
rename ::repair_timing_helper ::ot_repair_timing_helper_orig
proc ::repair_timing_helper { args } {
  puts "OT_HOLD_CAP repair_timing -max_buffer_percent $::ot_mbp -max_iterations $::ot_mit"
  ::ot_repair_timing_helper_orig {*}$args -max_buffer_percent $::ot_mbp -max_iterations $::ot_mit
}
