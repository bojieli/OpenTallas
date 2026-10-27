# GENERATED-COPY of tools/die_plan/hold_repair_pre.tcl (PRE_GLOBAL_ROUTE hook of clock.io_hold plan_demand kits only,
# HOLD-REPAIR 2026-10-26, METHODOLOGY 12.4a a1): the FF GRT hold repair pads the plan-declared seam hold demand on the
# receiving tile's input DATA paths.  Clock network untouched; constraints, margins and corners unchanged.
#  1. the standard GRT hook (grt_pre.tcl: FF vclk binding, optional max-wire repeaters);
#  2. hold_pad_hb4.tcl (physical/common_flow): HB4xp67 allowed ONLY inside repair_timing -hold (~47 ps FF per cell vs
#     BUFx2 ~17 ps: ~2.4x fewer pad cells, pins and nets for the same delay);
#  3. buffer cap: ORFS repair_timing's default 20 % buffer cap (RSZ-0060) is below a seam-heavy tile's demand
#     (2-5 HB4 per receiving seam bit); OT_MAX_BUFFER_PERCENT (default 100) raises the tool cap only.
# The inserted count is logged (OT_HB4PAD ... holds N) for the per-die census (hold_demand.hold_cell_census).
set hr_dir [file dirname [file normalize [info script]]]
source [file join $hr_dir grt_pre.tcl]
source [file join $hr_dir hold_pad_hb4.tcl]
set ::ot_hr_mbp [expr {[info exists ::env(OT_MAX_BUFFER_PERCENT)] && $::env(OT_MAX_BUFFER_PERCENT) ne "" ? $::env(OT_MAX_BUFFER_PERCENT) : 100}]
if {[llength [info procs ::repair_timing_helper]] && ![llength [info procs ::ot_hr_rth_orig]]} {
  rename ::repair_timing_helper ::ot_hr_rth_orig
  proc ::repair_timing_helper {args} {
    puts "OT_HOLD_REPAIR repair_timing -max_buffer_percent $::ot_hr_mbp"
    ::ot_hr_rth_orig {*}$args -max_buffer_percent $::ot_hr_mbp
  }
}
