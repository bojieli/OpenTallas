# HEAD-CORE-R14 2026-10-27 (COORD RULING HEAD-CORE-R13 ASK3, flow change behind the head flow canary):
# GRT-stage repair_design on UNSCALED wire RC with a >= 20 % slew/cap margin.
#
# Measured failure (HEAD-CORE-R13, results/physical/head_core_r13/README.md root cause 1): elemA TT slew 8 / elemB TT 9 +
# FF 1 after route.  Same cone in both cores: INVx1 -> OA21x2 .A1 121-146 um away on one row; routed RCX 321-395 ps vs
# the 320 ps limit.  The ORFS GRT repair_design (SLEW_MARGIN 20 already set) ran on the kit's LAYER_PARASITICS_FILE =
# cf/rc_cal.tcl with OT_RC_CAL 0.8,0.9 (R x0.8, C x0.9: tuned so the GRT CLOCK arrival matches RCX), i.e. ~0.72x the
# RC of a long signal wire, so the 20 % margin did not cover it.
#
# Fix: source this file from the kit's PRE_GLOBAL_ROUTE_TCL (after drv.tcl).  It wraps repair_design so that, when it is
# called after global routing exists (the ORFS GRT repair_design_helper), the GRT parasitics are re-estimated with the
# platform setRC.tcl (unscaled; stock C is >= RCX on M2-M7, so this is the pessimistic side for data DRV), repair_design
# runs with -slew_margin/-cap_margin >= OT_GRT_DRV_MARGIN (default 20), and the kit's calibrated RC (rc_cal) is restored
# and re-estimated so every later GRT step (hold repair, clock reports) keeps the clock-calibrated estimate.
# Data nets only in effect: the clock nets are plan-built and dont_touch (mscts_h), repair_design does not buffer them.
# Calls before global routing (placement-stage repair) pass through unchanged.  Idempotent per process.
if {![llength [info procs ::hd_grt_rd_orig]] && [llength [info commands ::repair_design]]} {
  rename ::repair_design ::hd_grt_rd_orig
  proc ::repair_design {args} {
    if {[catch {grt::have_routes} gr] || !$gr} {
      return [uplevel 1 [list ::hd_grt_rd_orig {*}$args]]
    }
    set m [expr {[info exists ::env(OT_GRT_DRV_MARGIN)] && $::env(OT_GRT_DRV_MARGIN) ne "" ? $::env(OT_GRT_DRV_MARGIN) : 20}]
    set a {}
    set skip 0
    foreach x $args {
      if {$skip} { set skip 0; continue }
      if {$x in {-slew_margin -cap_margin}} { set skip 1; continue }
      lappend a $x
    }
    set i [lsearch -exact $args -slew_margin]
    set sm [expr {$i >= 0 ? max([lindex $args [expr {$i + 1}]], $m) : $m}]
    set i [lsearch -exact $args -cap_margin]
    set cm [expr {$i >= 0 ? max([lindex $args [expr {$i + 1}]], $m) : $m}]
    set base [expr {[info exists ::env(OT_RC_BASE)] && $::env(OT_RC_BASE) ne "" ? $::env(OT_RC_BASE) : "/OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl"}]
    set n0 [sta::max_slew_violation_count]
    source $base
    estimate_parasitics -global_routing
    set n1 [sta::max_slew_violation_count]
    puts "HD_GRT_DRV unscaled RC ($base): max-slew violators [format %d $n0] (kit RC) -> [format %d $n1] (unscaled); repair_design -slew_margin $sm -cap_margin $cm"
    set rc [catch {uplevel 1 [list ::hd_grt_rd_orig {*}$a -slew_margin $sm -cap_margin $cm]} out opts]
    set n2 [sta::max_slew_violation_count]
    if {[info exists ::env(LAYER_PARASITICS_FILE)] && [file exists $::env(LAYER_PARASITICS_FILE)]} {
      source $::env(LAYER_PARASITICS_FILE)
    }
    estimate_parasitics -global_routing
    puts "HD_GRT_DRV after repair: unscaled-RC violators $n2; kit RC restored, violators [sta::max_slew_violation_count]"
    return -options $opts $out
  }
}
