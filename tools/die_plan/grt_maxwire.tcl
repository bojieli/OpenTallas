# PRE_GLOBAL_ROUTE hook (opt-in gen.py phys --max-wire-um UM; ELEM-S81 station405 2026-10-24): repeater pitch on every
# signal net for the post-GRT repair_design.
# Why: station405 B t11 / t31 / t34 / t1 routed with TT setup + FF hold met but failed DRV max slew (t11 4, t34 2, t1 5,
# t31 27 pins; limit 320 ps, worst 386.7).  Probe of t31 6_final.odb: every violator is ONE driven segment ~150 um long
# on M2/M3 (u_ft_ft0_s0/q[501] QN -> BUFx3 place13387 at the face (115.5,5.4) -> 150 um -> INVx1 _1708_ (115.7,155.5)
# -> station-1 wire buffer): repair_design at GRT (SLEW_MARGIN 50, GRT-estimated RC, FF libs since run_kit.sh repairs
# at CORNERS=bc) saw it in limit; RCX on the detailed route (M2/M3, high R) put it 20 % over.  Industry practice: a
# maximum repeater pitch on every signal net, so the slew is set by repeater spacing and not by the layer the detailed
# router happens to use (same remedy as physical/common_flow/max_wire_repeat.tcl, S81-CAPC 10-19, and
# hbm_lk_ep grt_drv_maxwire.tcl, HBM 10-11).  This keeps the flow's own repair_design (same SLEW/CAP margins) and only
# adds -max_wire_length OT_MAXWIRE_UM.  Clock nets are untouched (repair_design skips them).  No limit, margin or
# constraint changes.
if {![info exists ::env(OT_MAXWIRE_UM)] || $::env(OT_MAXWIRE_UM) eq ""} { error "grt_maxwire.tcl: OT_MAXWIRE_UM unset" }
# DIE-S81-85 2026-11-09 MAXWIRE-183 (serdes14_vR 5_1_grt GRT-0183 inside 'OT_MAXWIRE repair_design', no OT_GRT183_RESUME_SAVED):
# grt183_resume.tcl is sourced BEFORE this kit hook and wraps repair_design_helper (catch GRT-0183 -> save -> one fresh
# re-run).  Renaming the helper here replaced that wrapper with a plain proc, so the incremental GRT-0183 of this
# repair_design escaped the class resume.  When the wrapper is present, the max-wire body replaces the wrapped INNER helper
# (ot_g183_orig_repair_design_helper) and the wrapper stays in front of it; without it, unchanged.
set ot_mw_target repair_design_helper
if {[llength [info commands ot_g183_orig_repair_design_helper]]} { set ot_mw_target ot_g183_orig_repair_design_helper }
if {[info procs $ot_mw_target] ne "" && [info procs ot_orig_repair_design_helper] eq ""} {
  rename $ot_mw_target ot_orig_repair_design_helper
  if {$ot_mw_target ne "repair_design_helper"} { puts "OT_MAXWIRE under GRT183-RESUME: wrapper repair_design_helper kept, max-wire body in $ot_mw_target" }
  proc $ot_mw_target {args} {
    set args [list -verbose -max_wire_length $::env(OT_MAXWIRE_UM)]
    if {[info exists ::env(CAP_MARGIN)] && $::env(CAP_MARGIN) ne ""} { lappend args -cap_margin $::env(CAP_MARGIN) }
    if {[info exists ::env(SLEW_MARGIN)] && $::env(SLEW_MARGIN) ne ""} { lappend args -slew_margin $::env(SLEW_MARGIN) }
    if {[info exists ::env(MATCH_CELL_FOOTPRINT)] && $::env(MATCH_CELL_FOOTPRINT)} { lappend args -match_cell_footprint }
    puts "OT_MAXWIRE repair_design $args"
    set n0 [sta::network_leaf_instance_count]
    log_cmd repair_design {*}$args
    puts "OT_MAXWIRE leaf instances $n0 -> [sta::network_leaf_instance_count]"
  }
} elseif {[info procs repair_design_helper] eq ""} {
  error "grt_maxwire.tcl: ORFS repair_design_helper not defined (flow scripts changed)"
}
