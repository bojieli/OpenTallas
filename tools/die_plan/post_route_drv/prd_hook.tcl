# FLOW-CLOCK-R7 2026-10-29: shared post-route drive (DRV) repair on the core's ROUTED RCX parasitics, one pass
# (ORFS POST_GLOBAL_ROUTE_TCL hook staged by tools/die_plan/post_route_drv/prd_mk.sh; die-agnostic, opt-in).
# Recipe = KV eco_route.tcl m-order (DRV first on the routed SPEF, setup, hold: the e1/e5/e7 signed-off order) started
# from the kit's PRE-DRT 5_1_grt.odb (FLOW-SHARED-10 grt form, ONE detailed route afterwards), with the three fixes the
# R6 HBM bdring canary measured (lanes/COORD-REVIEW-QUEUE.md 10-29 16:31):
#   (1) the two-mode hold session: the runner patches orfs_hold_mm.py into the container (kit_modes_eco.tcl checks it);
#   (2) clock-freeze cells keep their masters: clk_freeze LOCKs every instance on a clock net, but sink flops are not
#       dont_touch (hold buffers must reach their D pins, RSZ-3006), so the R6 setup repair upsized 33 LOCKED
#       DFFHQNx1 -> x2 in place = 16 overlaps at fill (DPL-0033).  Here every master family used by a clock-net sink is
#       set_dont_use for the ECO session (no sink can be resized; buffering at its pins is unchanged), and a fail-safe
#       guard reverts + reports any frozen instance whose master still changed before legalization;
#   (3) the <= 2-pass loop is in prd_run.sh (re-extract RCX after DRT, repeat only while slew/cap violations remain).
# Limits are the existing sign-off ones (liberty max_transition / max_capacitance; no fanout limit unless
# OT_PRD_MAX_FANOUT opts in (R8), repair margins 20 %); no corner, margin or check kind changes.
#   OT_MAX_FANOUT OT_SLEW_MARGIN OT_SETUP_MARGIN OT_HOLD_MARGIN OT_HOLD_ALLOW_SETUP OT_HOLD_MAXBUF  (as eco_route.tcl)
#   OT_PRD_PASS (1|2, log only)
set _here [file dirname [info script]]
# FLOW-11 10-30 (DIE-QC-50 BTAB, CHECKED there): the ECO session read the routed SPEF once, but every later
# estimate_parasitics (two-mode ot_mm_sync before each repair, ot_rc_cal_hold, the measured-FF IO frame of
# vclk_measured_hold.tcl, the kit's post-GRT hook) overwrote it with the global-route estimate, so hold repair and the
# IO virtual-clock frame were timed on estimates, not on the routed DB (BTAB wd_in[227]: session 22.82 vs sign-off
# -4.29; -4.29 once the routed SPEF is re-read).  ot_prd_spef_arm reads the routed SPEF into every scene of the session
# (two-mode: the setup scene and BC; else the one corner) and re-reads it after each native estimate_parasitics:
# every existing net keeps its routed RCX parasitics, nets the ECO creates keep the estimate.  No check or margin
# changes.  OT_PRD_ROUTED_SPEF=0 = the old single read (A/B only).
proc ot_prd_spef_read {why} {
  set f $::ot_prd_spef
  set scs {}
  if {[info exists ::ot_mm_active] && $::ot_mm_active && [llength [info commands ot_mm_sc]]} {
    set scs [list [ot_mm_sc] BC]
    foreach sc $scs { read_spef -corner $sc $f }
  } else {
    read_spef $f
  }
  incr ::ot_prd_spef_reads
  puts "OT_PRD_SPEF $why: read_spef [expr {[llength $scs] ? "-corner {$scs} " : ""}][file tail $f] (read $::ot_prd_spef_reads)"
}
proc ot_prd_spef_arm {f} {
  if {[info exists ::env(OT_PRD_ROUTED_SPEF)] && $::env(OT_PRD_ROUTED_SPEF) eq "0"} {
    puts "OT_PRD_SPEF off (OT_PRD_ROUTED_SPEF=0): one read, later estimates overwrite it"
    read_spef $f
    return
  }
  set ::ot_prd_spef $f
  set ::ot_prd_spef_reads 0
  ot_prd_spef_read entry
  if {[llength [info commands ::ot_prd_native_estimate]]} { return }
  # no native estimator in this interpreter (tclsh harnesses, sessions without RSZ): nothing to re-read after
  if {![llength [info commands ::estimate_parasitics]]} { return }
  rename ::estimate_parasitics ::ot_prd_native_estimate
  proc ::estimate_parasitics {args} {
    set r [uplevel 1 [list ::ot_prd_native_estimate {*}$args]]
    ot_prd_spef_read "after estimate_parasitics $args"
    return $r
  }
}
if {[info exists ::env(OT_MM_FROZEN_CLOCK_SPEFS)] && $::env(OT_MM_FROZEN_CLOCK_SPEFS) ne ""} {
  # The native estimator already supplied DATA RC and the early MM callback
  # restored only the immutable frozen clock. Never replay an old full SPEF or
  # reset the original freeze baseline here.
  if {![llength [info commands ::ot_mm_frozen_clock_rc_restore]]} {
    error "OT_MM_FROZEN_CLOCK_RC: early lifecycle helper missing before PRD"
  }
  ::ot_mm_frozen_clock_rc_restore prd_entry
} else {
  ot_prd_spef_arm $::env(RESULTS_DIR)/6_final.spef
  set _ckf [file join $_here clk_freeze.tcl]
  if {![file exists $_ckf]} { error "OT_CLK_FREEZE FAIL: $_ckf not staged (ECO refuses to run without the clock lock)" }
  source $_ckf
  ot_clk_freeze
}
global_route -start_incremental
set _pass [expr {[info exists ::env(OT_PRD_PASS)] ? $::env(OT_PRD_PASS) : 1}]

# instances on clock nets (as ot_clk_freeze): drivers = clock-tree cells (dont_touch there), the rest = sinks
proc ot_prd_clock_insts {} {
  set masters [dict create]
  foreach n [ot_clk_dbnets] {
    foreach it [$n getITerms] {
      set i [$it getInst]
      dict set masters [$i getName] [[$i getMaster] getName]
    }
  }
  return $masters
}
# ASAP7 drive-strength family of a master: DFFHQNx1_ASAP7_75t_R -> DFFHQNx*_ASAP7_75t_R (one pattern per family)
proc ot_prd_family {m} {
  if {[regsub {x[0-9][0-9A-Za-z]*(_ASAP7_.*)$} $m {x*\1} f]} { return $f }
  return $m
}
set ::ot_prd_masters [ot_prd_clock_insts]
set _fams [dict create]
dict for {i m} $::ot_prd_masters {
  set inst [[ord::get_db_block] findInst $i]
  if {[$inst isDoNotTouch]} continue
  # a buffer / inverter / hold-cell family stays usable (repair needs it); such a sink is covered by the revert guard
  if {[regexp {^(BUF|INV|HB[0-9]|CKINV)} $m]} continue
  dict set _fams [ot_prd_family $m] 1
}
set _du 0
foreach f [lsort [dict keys $_fams]] {
  set lc [get_lib_cells -quiet */$f]
  if {[llength $lc]} { set_dont_use $lc; incr _du [llength $lc] }
}
puts "OT_PRD pass $_pass sink guard: [dict size $::ot_prd_masters] clock-net instances, [dict size $_fams] sink master families -> set_dont_use $_du lib cells for the ECO session: [lsort [dict keys $_fams]]"

if {$::env(OT_MAX_FANOUT) > 0} { set_max_fanout $::env(OT_MAX_FANOUT) [current_design] }
puts "OT_PRD pass $_pass repair_design slew_margin $::env(OT_SLEW_MARGIN) cap_margin $::env(OT_SLEW_MARGIN) max_fanout $::env(OT_MAX_FANOUT) (routed RCX SPEF)"
set _drv_args [list -slew_margin $::env(OT_SLEW_MARGIN) -cap_margin $::env(OT_SLEW_MARGIN)]
# Optional geometric data-net segmentation, independent of the Liberty slew
# repair decision. Frozen clock nets/drivers remain protected by ot_clk_freeze.
set _wire_limit [expr {[info exists ::env(OT_PRD_MAX_WIRE_LENGTH)] ? $::env(OT_PRD_MAX_WIRE_LENGTH) : 0}]
if {![string is double -strict $_wire_limit] || $_wire_limit < 0} {error "OT_PRD invalid max wire length $_wire_limit"}
if {$_wire_limit > 0} {lappend _drv_args -max_wire_length $_wire_limit}
puts "OT_PRD pass $_pass repair_design $_drv_args"
repair_design {*}${_drv_args}
if {$::env(OT_SETUP_MARGIN) ne ""} {
  puts "OT_PRD pass $_pass repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN)"
  repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN) -skip_last_gasp
}
set args [list -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
# two-mode kits: the SHARED guarded hold repair of orfs_hold_mm.tcl (R5 chunk buffer cap inside the same total budget,
# met-first, stall + time limits, FF clock RC calibration) -- R7 KV canary: one raw call sat >30 min in iteration 0 on
# 9,048 margin endpoints at real ws -10.5 (the E0 plateau class).  Kits without the session keep the raw call.
if {[llength [info commands ot_repair_hold_guarded]] && [ot_hold_guard_on]} {
  puts "OT_PRD pass $_pass hold: shared guarded repair (orfs_hold_mm.tcl) $args"
  ot_rc_cal_hold { ot_repair_hold_guarded $args }
} else {
  puts "OT_PRD pass $_pass repair_timing -hold $args"
  repair_timing -hold {*}$args
}

# fail-safe: any clock-net instance whose master changed is put back (LOCKED cells are never legalized, so a grown
# master overlaps its neighbours); the count is reported, a revert that cannot be applied stops the ECO
proc ot_prd_sink_revert {} {
  set block [ord::get_db_block]
  set rev {}
  dict for {i m} $::ot_prd_masters {
    set inst [$block findInst $i]
    if {$inst eq "NULL" || $inst eq ""} { error "OT_PRD FAIL: clock-net instance $i vanished in the ECO" }
    set now [[$inst getMaster] getName]
    if {$now ne $m} {
      if {[catch {replace_cell [get_cells -quiet $i] [lindex [get_lib_cells */$m] 0]} msg]} {
        error "OT_PRD FAIL: cannot restore $i $now -> $m: $msg"
      }
      if {[[$inst getMaster] getName] ne $m} { error "OT_PRD FAIL: $i still $now after restore" }
      lappend rev "$i:$now->$m"
    }
  }
  puts "OT_PRD sink guard: [llength $rev] clock-net instance masters restored [lrange $rev 0 19]"
  return [llength $rev]
}
set ::ot_prd_reverted [ot_prd_sink_revert]
# OT_PAD_MASTERS as eco_route.tcl (DRT pin access around abutted ECO buffers)
if {[info exists ::env(OT_PAD_MASTERS)] && $::env(OT_PAD_MASTERS) ne ""} {
  foreach mp $::env(OT_PAD_MASTERS) {
    lassign [split $mp :] m n
    set_placement_padding -masters [list $m] -left $n -right $n
  }
}
detailed_placement
if {[catch {check_placement} msg]} { error "OT_PRD FAIL: check_placement after the ECO legalization: $msg" }
global_route -end_incremental
ot_clk_freeze_assert post_grt
# FLOW-12 opt-in OT_PRD_FROM=route (prd_mk.sh): the ECO started from the ROUTED DB -> rip only the nets it touched,
# keep every other net's routed wires for an incremental detailed route (prd_route_keep.tcl)
if {[info exists ::env(OT_PRD_FROM)] && $::env(OT_PRD_FROM) eq "route"} {
  source [file join $_here prd_route_keep.tcl]
  ot_prd_route_keep
}
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
puts "OT_PRD pass $_pass hook done (sink masters restored $::ot_prd_reverted)"
