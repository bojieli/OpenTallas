# ELEM-HBM 10-24 (PRE_GLOBAL_ROUTE hook): the CP1-R10 kit IO standard (input min delay -insertion_tol vs the IO virtual
# clock at the plan insertion) asks every pin-registered input for ~45-90 ps of hold delay; on 4-6k-input cores that
# exceeds ORFS repair_timing's default 20 % buffer cap (RSZ-0060).  Raise the tool cap only (OT_MAX_BUFFER_PERCENT,
# default 100); constraints, margins and corners are unchanged.
set ot_mbp [expr {[info exists ::env(OT_MAX_BUFFER_PERCENT)] ? $::env(OT_MAX_BUFFER_PERCENT) : 100}]
rename repair_timing_helper ot_repair_timing_helper_orig
proc repair_timing_helper { args } {
  global ot_mbp
  puts "OT_HOLD_CAP repair_timing -max_buffer_percent $ot_mbp"
  ot_repair_timing_helper_orig {*}$args -max_buffer_percent $ot_mbp
}
