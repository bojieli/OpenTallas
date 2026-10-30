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
# Limits are the existing sign-off ones (liberty max_transition / max_capacitance, the kit's max_fanout basis 24,
# repair margins 20 %); no corner, margin or check kind changes.
#   OT_MAX_FANOUT OT_SLEW_MARGIN OT_SETUP_MARGIN OT_HOLD_MARGIN OT_HOLD_ALLOW_SETUP OT_HOLD_MAXBUF  (as eco_route.tcl)
#   OT_PRD_PASS (1|2, log only)
set _here [file dirname [info script]]
read_spef $::env(RESULTS_DIR)/6_final.spef
set _ckf [file join $_here clk_freeze.tcl]
if {![file exists $_ckf]} { error "OT_CLK_FREEZE FAIL: $_ckf not staged (ECO refuses to run without the clock lock)" }
source $_ckf
ot_clk_freeze
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
repair_design -slew_margin $::env(OT_SLEW_MARGIN) -cap_margin $::env(OT_SLEW_MARGIN)
if {$::env(OT_SETUP_MARGIN) ne ""} {
  puts "OT_PRD pass $_pass repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN)"
  repair_timing -setup -setup_margin $::env(OT_SETUP_MARGIN) -skip_last_gasp
}
set args [list -hold -hold_margin $::env(OT_HOLD_MARGIN) -max_buffer_percent $::env(OT_HOLD_MAXBUF)]
if {$::env(OT_HOLD_ALLOW_SETUP) == 1} { lappend args -allow_setup_violations }
puts "OT_PRD pass $_pass repair_timing $args"
repair_timing {*}$args

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
estimate_parasitics -global_routing
write_guides $::env(RESULTS_DIR)/route.guide
puts "OT_PRD pass $_pass hook done (sink masters restored $::ot_prd_reverted)"
