# GENERATED-COPY of tools/die_plan/hold_repair_pre.tcl (PRE_GLOBAL_ROUTE hook of clock.io_hold plan_demand kits only,
# HOLD-REPAIR 2026-10-26, METHODOLOGY 12.4a a1): the FF GRT hold repair pads the plan-declared seam hold demand on the
# receiving tile's input DATA paths.  Clock network untouched; constraints, margins and corners unchanged.
#  1. the standard GRT hook (grt_pre.tcl: FF vclk binding, optional max-wire repeaters);
#  2. hold_pad_hb4.tcl (physical/common_flow): HB4xp67 allowed ONLY inside repair_timing -hold (~47 ps FF per cell vs
#     BUFx2 ~17 ps: ~2.4x fewer pad cells, pins and nets for the same delay);
#  3. buffer cap: ORFS repair_timing's default 20 % buffer cap (RSZ-0060) is below a seam-heavy tile's demand
#     (2-5 HB4 per receiving seam bit); OT_MAX_BUFFER_PERCENT (default 100) raises the tool cap only.
# The inserted count is logged (OT_HB4PAD ... holds N) for the per-die census (hold_demand.hold_cell_census).
#  4. R-FLOW hold budget (RULES-FLOW-1 2026-11-13, coord lanes/RULEBOOK-1113.md): the OT_HOLD_BUDGET line reports the
#     cells this repair_timing call added against the placed logic cells and OT_HOLD_BUDGET_PCT (default 10).  Report
#     only.  OVER is not a flow problem: the pairs are unbalanced by structure (R-CLOCK), so no margin or cap is raised.
#     The repair target stays HOLD_SLACK_MARGIN of the FF GRT step (0): a +30 ps target was tried on HEAD hd_turn_b and
#     padded every zero-logic landing-ring pair (631 -> 3,323 cells, 18.5 % of the logic cells, for 47 routed endpoints).
set hr_dir [file dirname [file normalize [info script]]]
source [file join $hr_dir grt_pre.tcl]
source [file join $hr_dir hold_pad_hb4.tcl]
set ::ot_hr_mbp [expr {[info exists ::env(OT_MAX_BUFFER_PERCENT)] && $::env(OT_MAX_BUFFER_PERCENT) ne "" ? $::env(OT_MAX_BUFFER_PERCENT) : 100}]
if {[llength [info procs ::repair_timing_helper]] && ![llength [info procs ::ot_hr_rth_orig]]} {
  rename ::repair_timing_helper ::ot_hr_rth_orig
  proc ::ot_hr_logic_cells {} {
    set n 0
    foreach i [[ord::get_db_block] getInsts] {
      if {![regexp {^(TAPCELL|FILLER|DECAP)} [[$i getMaster] getName]]} { incr n }
    }
    return $n
  }
  proc ::repair_timing_helper {args} {
    puts "OT_HOLD_REPAIR repair_timing -max_buffer_percent $::ot_hr_mbp"
    set n0 [::ot_hr_logic_cells]
    set rc [catch {::ot_hr_rth_orig {*}$args -max_buffer_percent $::ot_hr_mbp} msg opts]
    set n1 [::ot_hr_logic_cells]
    set lim [expr {[info exists ::env(OT_HOLD_BUDGET_PCT)] && [string is double -strict $::env(OT_HOLD_BUDGET_PCT)] ? $::env(OT_HOLD_BUDGET_PCT) : 10.0}]
    set pct [expr {$n0 > 0 ? 100.0 * ($n1 - $n0) / $n0 : 0.0}]
    set hw "n/a"; catch { set hw [format %.2f [worst_slack -min]] }
    puts [format "OT_HOLD_BUDGET added %d logic_cells %d pct %.2f budget %g hold_ws %s margin %s %s" [expr {$n1 - $n0}] $n0 $pct $lim $hw \
      [expr {[info exists ::env(HOLD_SLACK_MARGIN)] ? $::env(HOLD_SLACK_MARGIN) : 0}] [expr {$pct > $lim ? "OVER" : "OK"}]]
    return -options $opts $msg
  }
}
