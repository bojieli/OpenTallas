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
    # REPAIR-NOPROGRESS (S81-CONG 11-16): grt183_make.sh stopped attempt 1 inside this repair (log flat OT_GRT_REPAIR_STALL_S) and
    # re-runs the stage once with this marker: the post-GRT repair_design is skipped, so the stage keeps the full route's
    # result and goes on to timing repair.  Max slew / cap DRV are advisory in the R-MINIMAL profile (OWNER 11-13) and stay
    # visible in the sign-off DRV report.
    # OT_MAXWIRE_POST_SKIP=1 (item_env / die_gen_env, WAVE-PILOT-FIX 11-19): the same skip from the first run on.  The nostall marker above lives in the job's results dir, and a route job that
    # is killed after its stall retry (ot-oom-age GUARD SIGKILL, make Error 247 / 241) is requeued with a fresh job dir: the marker is gone and the repair stalls again for 30 min before the
    # next retry.  A type known to stall sets this and never enters the single-thread incremental-FastRoute repair.
    if {([info exists ::env(OT_MAXWIRE_POST_SKIP)] && $::env(OT_MAXWIRE_POST_SKIP) eq "1") ||
        ([info exists ::env(RESULTS_DIR)] && [file exists $::env(RESULTS_DIR)/5_1_grt.repair_nostall.json])} {
      puts "OT_MAXWIRE_PASS post skipped: no-progress stop in attempt 1 (5_1_grt.repair_nostall.json) or OT_MAXWIRE_POST_SKIP=1; full-route result kept, stage continues (max slew / cap DRV advisory)"
      return
    }
    # FLOW-GRT-RESID 11-21 (COORD, FAM-KV-HUB: the flat-repair kill at 01:43 re-ran the whole GRT and lost 5.5 h): save the full-route design BEFORE this repair, so the
    # grt183_make.sh no-progress continue path resumes from it and skips only this step (5_1_grt.prerepair.odb, see grt_stall_resume.tcl).
    if {[llength [info commands ::ot_gstall::save_pre]]} { catch {::ot_gstall::save_pre} }
    puts "OT_MAXWIRE repair_design $args"
    set n0 [sta::network_leaf_instance_count]
    set t0 [clock seconds]
    log_cmd repair_design {*}$args
    puts "OT_MAXWIRE leaf instances $n0 -> [sta::network_leaf_instance_count]"
    puts "OT_MAXWIRE_PASS post done: +[expr {[sta::network_leaf_instance_count] - $n0}] cells in [expr {[clock seconds] - $t0}] s (GRT parasitics, pitch $::env(OT_MAXWIRE_UM) um)"
  }
} elseif {[info procs repair_design_helper] eq ""} {
  error "grt_maxwire.tcl: ORFS repair_design_helper not defined (flow scripts changed)"
}
# S81-CONG MAXWIRE-PRE 2026-11-16 (FABLE-FIX-S81-CONG), OPT-IN (OT_MAXWIRE_PRE=1), default OFF.  The post-GRT max-wire
# repair_design inserts 20-40 k repeaters on GRT parasitics; each parasitics refresh inside it legalizes and re-routes every
# touched net with the single-thread incremental FastRoute (perf on c_t34 / c_t47: 82 % mazeRouteMSMDSequential): 5.6 h
# silent on t68 between table rows 56,000 and 57,000 of 146,176, 3.5 h+ on t65.  This pass sets the same pitch BEFORE
# global_route on placement parasitics (same command and margins) so the one full route sees the repeaters: 287 s on
# leaf t34 (38,965 repeaters in 33,709 nets).  MEASURED on that kit (m_t34 against c_t34, same 4_cts.odb): the full route
# then ends at overflow 30 (2D; it5 440, it15 24, it30 30, GRT-0116) where the route without repeaters ends at 0 by
# iteration 12; the residual sits in the 18-um channel between ve_m / vs / vsw (x 240..260, y 420..440), where the
# repeaters of nets crossing the 225-um vsw core are pushed.  So it is NOT the default; kept for types without wide cores.
if {[info exists ::env(OT_MAXWIRE_PRE)] && $::env(OT_MAXWIRE_PRE) eq "1"} {
  set ot_mwp_args [list -verbose -max_wire_length $::env(OT_MAXWIRE_UM)]
  if {[info exists ::env(CAP_MARGIN)] && $::env(CAP_MARGIN) ne ""} { lappend ot_mwp_args -cap_margin $::env(CAP_MARGIN) }
  if {[info exists ::env(SLEW_MARGIN)] && $::env(SLEW_MARGIN) ne ""} { lappend ot_mwp_args -slew_margin $::env(SLEW_MARGIN) }
  if {[info exists ::env(MATCH_CELL_FOOTPRINT)] && $::env(MATCH_CELL_FOOTPRINT)} { lappend ot_mwp_args -match_cell_footprint }
  if {[info exists ::env(DONT_USE_CELLS)] && $::env(DONT_USE_CELLS) ne ""} { set_dont_use $::env(DONT_USE_CELLS) }
  set ot_mwp_n0 [sta::network_leaf_instance_count]
  set ot_mwp_t0 [clock seconds]
  log_cmd estimate_parasitics -placement
  puts "OT_MAXWIRE_PRE repair_design $ot_mwp_args"
  log_cmd repair_design {*}$ot_mwp_args
  if {[info exists ::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)] && $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) ne ""} {
    set_placement_padding -global -left $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT) -right $::env(CELL_PAD_IN_SITES_DETAIL_PLACEMENT)
  }
  set ot_mwp_dpl {}
  if {[info exists ::ot_kit_dpl_args]} { set ot_mwp_dpl $::ot_kit_dpl_args } \
  elseif {[info exists ::env(DETAIL_PLACEMENT_ARGS)]} { set ot_mwp_dpl $::env(DETAIL_PLACEMENT_ARGS) }
  log_cmd detailed_placement {*}$ot_mwp_dpl
  # the kit legalizer (diamond, bounded displacement) can leave a few repeaters illegal in a full strip (m_t34: 2 of
  # 38,965); one pass of the default legalizer takes them, as the flow's own post-repair detailed_placement does.  Not
  # fatal here: the flow legalizes and runs check_placement -verbose again after the post-GRT repairs.
  if {[catch {check_placement} ot_mwp_err]} {
    puts "OT_MAXWIRE_PRE kit legalizer left illegal cells ($ot_mwp_err); default detailed_placement pass"
    log_cmd detailed_placement
    if {[catch {check_placement} ot_mwp_err]} { puts "OT_MAXWIRE_PRE WARNING placement still not legal before global_route: $ot_mwp_err" }
  }
  puts "OT_MAXWIRE_PASS pre done: +[expr {[sta::network_leaf_instance_count] - $ot_mwp_n0}] cells in [expr {[clock seconds] - $ot_mwp_t0}] s (placement parasitics, pitch $::env(OT_MAXWIRE_UM) um, before global_route)"
}
