# HBM-CTS-LEAFSLEW (DIE-HBM-59, COORD 2026-11-02 23:2x): clock-tree level/leaf nets are repeated post-CTS, before the
# tap/leaf balance.  Why: TritonCTS buffers a branch only beyond -distance_between_buffers along its own H-tree
# segments, and -repair_clock_nets repairs only the ROOT wire (port -> root buffer).  A branch point in the core
# middle then drives its leaf buffers on the face rows with one unbuffered star wire (calendar_f20
# clknet_4_2__leaf_clk: BUFx24 at y 90 -> 5 leaf BUFx24 at y 6-8, 85-116 um, 40 fF wire): routed slew 325-340 ps at
# the leaf inputs > the 320-ps max_transition, and the post-route late ECO may not touch clock nets.  Same class on
# vmdel_lane_n (13 leaves, 323-382 ps).
# Rule (per clock net driven by a clock buffer/inverter, never the root port net): every load lies within
# OT_CLK_LEAF_MAX_UM (default 50 um, Manhattan) of its driver, and a net whose loads are all clock buffers/inverters
# drives at most OT_CLK_LEAF_MAX_FANOUT (default 12; 0 = no cap) of them.  A violating net gets one repeater per load
# group (greedy groups: the farthest load + every other far load within OT_CLK_LEAF_MAX_UM/2 of it, at most the fanout
# cap), placed half way between the driver and the group centroid, same master as the driver (clock buffers) else
# OT_CLK_LEAF_CELL; passes repeat until the rule holds (at most OT_CLK_LEAF_PASSES, default 6), then the cells are
# legalised.  The tap/leaf balance that runs after this hook sees the final tree, so tap insertion targets are
# unchanged.  No gate changes.  OT_CLK_LEAF_REPEAT=0 = off (old behaviour).  Then OT_CLR_NEXT_TCL is sourced.
# DIE-HBM-60/LEAFSLEW 11-03 slew gate (default on): the distance-only rule above repeated 30 nets on calendar_f20 and
# 12 on vmdel_lane_n; the extra stage on some leaves raised each tap tree's MAX sink, so the tap balance (pad capped at
# target + window - max) left the pin-register mean 22 ps short of the vclk bound (calendar FAIL_POSTCTS TT dev 22.1).
# Now a net is repeated only when its placement-estimated worst load slew exceeds OT_CLK_LEAF_SLEW_PS (default 80 ps;
# calendar 4_cts: the routed 340-ps net clknet_4_2__leaf_clk estimates 101 ps, every net that stayed < 320 routed
# estimates <= 118 ps; vmdel: the routed 323-382-ps net estimates 165 ps) AND it is a branch net (all loads clock
# buffers/inverters), or its estimate exceeds 2x the gate.  Inside such a net EVERY load goes behind a repeater
# (sibling leaves keep one common depth), grouped as above.  OT_CLK_LEAF_SLEW_PS=0 = the distance-only rule.
# KW-FIX-17 11-05 (COORD 16:4x): copied into the repo from die-hbm-66/forms/fhp12 as the default-on kit-wave class
# fix.  tools/autopilot/kit_wave.py stages this file into a relaunched kit whose routed TT sign-off showed max_slew
# violations on clock-tree cell / register clock pins (LEAFSLEW signature) and appends to its config.mk:
#   export OT_CLR_NEXT_TCL := $(POST_CTS_TCL)
#   override export POST_CTS_TCL = /work/clk_leaf_repeat.tcl
# so the kit's own POST_CTS_TCL hook (if any) still runs after this one.  An unset / empty OT_CLR_NEXT_TCL sources
# nothing; one naming this file itself is ignored (no recursion).
# KW-FIX-24/LEAFREP 11-06 (COORD 20:0x (5) + 20:2x (6)): DEFAULT ON for every kit, not only the LEAFSLEW retry.
#   * CTS: physical/common_flow/grt183_make.sh (the make wrapper of every kit runner: gen_phys RUN_KIT, S81 / QC / KV /
#     HBM core runners) patches the disposable container's ORFS cts.tcl to source /work/clk_leaf_repeat_default.tcl
#     (this file, staged by tools/die_plan/core_flow.stage_grt183) right before 'source_step_tcl POST CTS', with
#     ::ot_clr_default set.  The default run is skipped when the kit hooks this file itself (POST_CTS_TCL names
#     clk_leaf_repeat.tcl, or its POST_CTS file / a /work file it sources names it, or OT_CLR_NEXT_TCL is set = the
#     kit-wave LEAFSLEW chain); then that hook runs it as before.  A second CTS run in one process is skipped
#     (::ot_clr_cts_done).  The default run never sources OT_CLR_NEXT_TCL.  Same rule and thresholds as above
#     (fanout cap 12, 50 um, 80-ps placement slew gate): no net over the rule = no change.
#   * GRT long-branch pass (::ot_clr_stage grt): S81 idx_tx vF: a single-load clock branch, 248 um routed over a
#     macro, routed TT slew 358 ps > 320, passed the 80-ps PLACEMENT-RC gate.  grt183_make.sh sources this file a
#     second time in ORFS global_route.tcl right after the first 'estimate_parasitics -global_routing' (routes and
#     GRT parasitics exist, before repair_design / repair_timing).  Candidates: clock-tree branch nets (driven by a
#     clock buffer / inverter, not a port; every load a clock buffer / inverter, or at most 2 loads) whose GLOBAL-ROUTE
#     wire length > OT_CLK_LEAF_LONG_UM (default 120 um; 0 = off) or that cross a macro (a GRT guide over a macro that
#     is not on the net) with routed length > OT_CLK_LEAF_MAX_UM; repeated when the GRT-RC estimated worst load slew
#     > OT_CLK_LEAF_GRT_SLEW_PS (default 150 ps, all session corners; 0 = length / macro rule alone).  Every load goes
#     behind a repeater (grouped as above), inside global_route -start_incremental / detailed_placement /
#     -end_incremental, at most OT_CLK_LEAF_GRT_PASSES (default 3) passes.  OT_CLK_LEAF_GRT=0 = no GRT pass.
#   OT_CLK_LEAF_REPEAT=0 (env or 'export OT_CLK_LEAF_REPEAT = 0' in config.mk) = both off (old behaviour).
# FLOW-LEAFREP-1121 (FABLE-FIX-KV-HUB / FABLE-PD-KV-0730 fix 2): the GRT pass above CREATES skew.  KV hroot D25d a5, per-sink
# TT arrival on GRT RC (FLOW-LEAFREP-1121 clkarr.tcl): post-hook CTS taps 217..290 ps, in-tap spread <= 70 ps on every
# clk_t*; after this pass clk_t9 233..749 ps (spread 510), t23 269, t14 202, t17 150, t40 124, 24 CLK pins over 320 ps.
# Mechanism: (1) every pass re-selects the nets the previous pass made (a repeater's output net still routes > 120 um
# to its far group, the driver's net too), so a 300-um branch is split d/2, d/4, d/8 ... = 7 BUFx24 in series in front of
# clkbuf_leaf_52_clk_t9, four of them 1 ps of wire apart (stacked at the group centroid: 17-26 ps of cell delay each);
# (2) only the long branch gets the stages, its sibling leaves of the same tap keep their depth, and nothing re-balances
# (partition kits run tapbal_grt / subtree_balance BEFORE this pass, or not at all).
# OT_CLK_LEAF_GRT_BAL=1 (balanced GRT repeat) changes the GRT pass only (CTS pass unchanged):
#   * one-shot chain: a repeated group gets k = ceil(d / OT_CLK_LEAF_LONG_UM) - 1 (>= 1, <= OT_CLK_LEAF_GRT_CHAIN_MAX,
#     default 4) repeaters EVENLY spaced on the driver -> group-centroid line (every segment <= the long rule), and the
#     repeated net plus every net the pass created are never candidates again (no halving chains, no stacked stages);
#   * latency guard: per repeated net the worst arrival at its ORIGINAL loads is read on GRT RC before and after; a net
#     whose repeat made its loads later by > OT_CLK_LEAF_GRT_RISE_PS (default 10 ps) while its unrepeated GRT slew was
#     within OT_CLK_LEAF_GRT_DRV_PS (default 320 ps = the max_transition sign-off limit) is restored (remove_buffers):
#     slew 150..320 ps is legal, a later branch is a skew defect;
#   * sibling balance: a tree whose kept repeats (DRV-forced: unrepeated slew > the limit) still made a branch later by
#     > OT_CLK_LEAF_GRT_RISE_PS gets subtree_balance.tcl (OT_STB_PORTS = those tree roots, GRT RC, tag lr, hard-core
#     subtrees fixed) in the same process, so its sibling leaves are delayed to the repeated branch.
#   Default 0 = the pass as before.  Every line says OT_CLK_LEAF_REPEAT grt bal ...
proc clr_is_clkcell {inst} {
  set m [[$inst getMaster] getName]
  return [expr {[string match "BUF*" $m] || [string match "INV*" $m] || [string match "CKINV*" $m] || [string match "CLKBUF*" $m]}]
}
proc clr_xy {inst} {
  set b [$inst getBBox]
  return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]]
}
# MACRO-CK-PIN class (S81-TYPES-5 11-07, serdes__t2 FAIL_POSTCTS FF -9932 ps on 3016 endpoints): a load on a hard macro
# was located at the macro's bbox centre.  The PMA TX macro is 2246 um wide and its ck pin sits 11 um from its left
# edge, so every repeater chased the centre 1100 um away and the last wire (repeater -> ck) stayed ~1950 um long:
# 7.3 ns wire delay + 2.2 ns library hold extrapolated from the slew at u_ptx/ck.  A load pin on a block master is
# now located at the pin itself (iterm bbox centre); standard-cell loads are unchanged (cell bbox centre).
proc clr_lxy {it} {
  set i [$it getInst]
  if {[[$i getMaster] isBlock]} {
    set b [$it getBBox]
    return [list [expr {([$b xMin] + [$b xMax]) / 2}] [expr {([$b yMin] + [$b yMax]) / 2}]]
  }
  return [clr_xy $i]
}
proc clr_is_clock_net {net} {
  if {[$net getSigType] eq "CLOCK"} { return 1 }
  return [string match "clknet*" [$net getName]]
}
# one net -> list of {driver_inst load_pairs} or "" when the net is not a repeatable clock-tree net
proc clr_net {net} {
  if {[llength [$net getBTerms]]} { return "" }
  set drv ""; set loads {}
  foreach it [$net getITerms] {
    if {[$it isOutputSignal]} { if {$drv ne ""} { return "" }; set drv [$it getInst]; continue }
    if {[$it isInputSignal]} { lappend loads $it }
  }
  if {$drv eq "" || ![clr_is_clkcell $drv] || [llength $loads] == 0} { return "" }
  return [list $drv $loads]
}
# KW-FIX-35-F2 11-08 (FLOW class F follow-up): CTS-stage legalization uses the kit's own 3_5 legalizer.  A bare
# detailed_placement is the negotiation legalizer at +-500 sites / +-100 rows; 3_5 of a diamond opt-in kit (FLOW-7,
# gen_phys DETAIL_PLACEMENT_ARGS) uses -use_diamond_legalizer over the whole outline.  QC sle_hc1__cl7d360508 a10
# (8134 FIRM ring flops in an 11.6-um S-face strip): 3_5 diamond 100 % legal in 7 s; CTS negotiation 1143 s, 512 left,
# leaf-repeat pass 505 left, retry 513 left (DPL-0033, 596 -> 604 overlaps: CTS clkbuf / clkload / wire repeaters vs
# movable u_cland ring logic + reset relays, 0 FIRM-vs-FIRM in 3_place).  S81 dsdv_slice_c1x_C__t3 a16R: 3897 s, 306 left.
# ORFS erases DETAIL_PLACEMENT_ARGS outside the place stage (variables.yaml stages: place; erase_non_stage_variables),
# so grt183_make.sh captures it in cts.tcl BEFORE the erase as ::ot_kit_dpl_args (OT_CTS_DPL_ARGS line); the env is the
# fallback (KEEP_VARS=1, or this file hooked elsewhere).
# clr_dpl_args: the kit args when they select the diamond legalizer, else none (unchanged).  escalate=1 (the residual
# retry): the diamond legalizer always (with the kit's -max_displacement when it has one), never the same stalled pass.
proc clr_dpl_args {{escalate 0}} {
  if {[info exists ::ot_kit_dpl_args]} { set a [string trim $::ot_kit_dpl_args]
  } else { set a [expr {[info exists ::env(DETAIL_PLACEMENT_ARGS)] ? [string trim $::env(DETAIL_PLACEMENT_ARGS)] : ""}] }
  if {[catch {llength $a}]} { set a "" }
  if {"-use_diamond_legalizer" in $a} { return $a }
  if {!$escalate} { return {} }
  return {-use_diamond_legalizer}
}
proc clr_kit_hooked {} {
  # the kit runs this file itself at POST_CTS (explicit hook / kit-wave LEAFSLEW chain)
  if {[info exists ::env(OT_CLR_NEXT_TCL)]} { return 1 }
  if {![info exists ::env(POST_CTS_TCL)] || [string trim $::env(POST_CTS_TCL)] eq ""} { return 0 }
  set todo [list [string trim $::env(POST_CTS_TCL)]]; set seen {}
  while {[llength $todo] && [llength $seen] < 64} {
    set f [lindex $todo 0]; set todo [lrange $todo 1 end]
    if {[lsearch -exact $seen $f] >= 0} continue
    lappend seen $f
    if {[file tail $f] eq "clk_leaf_repeat.tcl"} { return 1 }
    if {[catch {set fh [open $f r]; set txt [read $fh]; close $fh}]} continue
    if {[string match "*clk_leaf_repeat*" $txt]} { return 1 }
    foreach {- s} [regexp -all -inline -line {^\s*source\s+\{?(/work/[A-Za-z0-9_.-]+\.tcl)\}?\s*$} $txt] { lappend todo $s }
  }
  return 0
}
# FLOW-LEAFREP-1121: worst (latest) TT rise arrival over a list of load iterms, "" when none is timed
proc clr_load_arr {loads} {
  set w ""
  foreach it $loads {
    set pp [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"]
    if {$pp eq "" || $pp eq "NULL"} continue
    set a [get_property $pp arrival_max_rise]
    if {$a eq "" || $a eq "INF" || $a eq "-INF"} continue
    if {$w eq "" || $a > $w} { set w $a }
  }
  return $w
}
# driver output -> latest load delay (ps): the repeat's own effect, not an upstream repeat in the same pass
proc clr_net_delay {drv loads} {
  set w [clr_load_arr $loads]
  if {$w eq ""} { return "" }
  foreach t [$drv getITerms] {
    if {![$t isOutputSignal]} continue
    set pp [sta::find_pin "[$drv getName]/[[$t getMTerm] getName]"]
    if {$pp eq "" || $pp eq "NULL"} break
    set a [get_property $pp arrival_max_rise]
    if {$a eq "" || $a eq "INF" || $a eq "-INF"} break
    return [expr {$w - $a}]
  }
  return ""
}
# the clock-tree root port of a driver instance (walks input nets up through buffers / inverters), "" when none
proc clr_root {drv} {
  set i $drv
  for {set d 0} {$d < 64} {incr d} {
    set n ""
    foreach t [$i getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set n [$t getNet]; break } }
    if {$n eq ""} { return "" }
    set bt [$n getBTerms]
    if {[llength $bt]} { return [[lindex $bt 0] getName] }
    set i ""
    foreach t [$n getITerms] { if {[$t isOutputSignal]} { set i [$t getInst]; break } }
    if {$i eq ""} { return "" }
  }
  return ""
}
# balanced GRT repeat: latency guard (restore latency-harmful, DRV-legal repeats) + sibling balance of DRV-forced ones
proc clr_bal_guard {} {
  upvar #0 clr_g_rec rec clr_g_order order clr_rise rise clr_drv drv clr_blk blk clr_g_bufs nb
  set undo {}; set late {}; set nkeep 0
  foreach nm $order {
    if {![info exists rec($nm)]} continue
    lassign $rec($nm) a0 s0 bufs d
    set n [$blk findNet $nm]
    set loads {}
    if {$n ne "NULL" && $n ne ""} {
      # original loads = the loads of the LAST repeater of each chain = every non-repeater load downstream; read them
      # through the repeater nets this net now drives
      foreach b $bufs {
        set bi [$blk findInst $b]; if {$bi eq "NULL" || $bi eq ""} continue
        foreach t [$bi getITerms] {
          if {![$t isOutputSignal] || [$t getNet] eq "NULL"} continue
          foreach l [[$t getNet] getITerms] { if {[$l isInputSignal] && ![string match "clkleafrepg_*" [[$l getInst] getName]]} { lappend loads $l } }
        }
      }
    }
    set a1 [clr_net_delay $d $loads]
    if {$a0 eq "" || $a1 eq ""} { incr nkeep; puts "OT_CLK_LEAF_REPEAT grt bal keep $nm: arrival not readable (before <$a0> after <$a1>, [llength $loads] loads)"; continue }
    set dr [expr {$a1 - $a0}]
    if {$dr > $rise && $s0 <= $drv} {
      puts [format "OT_CLK_LEAF_REPEAT grt bal restore %s: driver->loads %.1f -> %.1f ps (+%.1f > %.0f), unrepeated slew %.1f <= %.0f ps, %d repeaters" $nm $a0 $a1 $dr $rise $s0 $drv [llength $bufs]]
      lappend undo {*}$bufs
    } else {
      incr nkeep
      puts [format "OT_CLK_LEAF_REPEAT grt bal keep %s: driver->loads %.1f -> %.1f ps (%+.1f), unrepeated slew %.1f ps, %d repeaters" $nm $a0 $a1 $dr $s0 [llength $bufs]]
      if {$dr > $rise} { set r [clr_root $d]; if {$r ne "" && $r ni $late} { lappend late $r } }
    }
  }
  if {[llength $undo]} {
    global_route -start_incremental
    remove_buffers {*}$undo
    detailed_placement {*}[clr_dpl_args]
    if {[catch {check_placement}]} { detailed_placement {*}[clr_dpl_args 1] }
    global_route -end_incremental
    estimate_parasitics -global_routing
    set nb [expr {$nb - [llength $undo]}]
  }
  puts [format "OT_CLK_LEAF_REPEAT grt bal: %d repeaters restored (latency-harmful, slew legal), %d repeated nets kept, %d trees to balance%s" \
          [llength $undo] $nkeep [llength $late] [expr {[llength $late] ? " ($late)" : ""}]]
  if {[llength $late] && [file exists /work/subtree_balance.tcl]} {
    set sv {}
    foreach k {OT_STB_PORTS OT_STB_EST OT_STB_TAG OT_STB_BLOCK_SINKS} { if {[info exists ::env($k)]} { dict set sv $k $::env($k) } }
    set ::env(OT_STB_PORTS) $late; set ::env(OT_STB_EST) grt; set ::env(OT_STB_TAG) lr
    if {![info exists ::env(OT_STB_BLOCK_SINKS)]} { set ::env(OT_STB_BLOCK_SINKS) fixed }
    uplevel #0 { source /work/subtree_balance.tcl }
    foreach k {OT_STB_PORTS OT_STB_EST OT_STB_TAG OT_STB_BLOCK_SINKS} { if {[dict exists $sv $k]} { set ::env($k) [dict get $sv $k] } else { unset -nocomplain ::env($k) } }
    estimate_parasitics -global_routing
  }
}
set ::ot_clr_mode [expr {[info exists ::ot_clr_stage] && $::ot_clr_stage eq "grt" ? "grt" : "cts"}]
set ::ot_clr_run 1
if {[info exists ::env(OT_CLK_LEAF_REPEAT)] && $::env(OT_CLK_LEAF_REPEAT) eq "0"} {
  set ::ot_clr_run 0
} elseif {$::ot_clr_mode eq "grt"} {
  if {[info exists ::env(OT_CLK_LEAF_GRT)] && $::env(OT_CLK_LEAF_GRT) eq "0"} { set ::ot_clr_run 0 }
} elseif {[info exists ::ot_clr_cts_done]} {
  puts "OT_CLK_LEAF_REPEAT already ran in this process: skipped"
  set ::ot_clr_run 0
} elseif {[info exists ::ot_clr_default] && [clr_kit_hooked]} {
  puts "OT_CLK_LEAF_REPEAT default: the kit hooks clk_leaf_repeat.tcl itself at POST_CTS; default run skipped"
  set ::ot_clr_run 0
}
if {$::ot_clr_run && $::ot_clr_mode eq "cts"} {
set ::ot_clr_cts_done 1
uplevel #0 {
  set clr_blk [ord::get_db_block]
  set clr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set clr_max_um [expr {[info exists ::env(OT_CLK_LEAF_MAX_UM)] ? double($::env(OT_CLK_LEAF_MAX_UM)) : 50.0}]
  set clr_fo [expr {[info exists ::env(OT_CLK_LEAF_MAX_FANOUT)] ? int($::env(OT_CLK_LEAF_MAX_FANOUT)) : 12}]
  set clr_cell_default [expr {[info exists ::env(OT_CLK_LEAF_CELL)] ? $::env(OT_CLK_LEAF_CELL) : "BUFx16f_ASAP7_75t_R"}]
  set clr_passes [expr {[info exists ::env(OT_CLK_LEAF_PASSES)] ? int($::env(OT_CLK_LEAF_PASSES)) : 6}]
  set clr_slew_ps [expr {[info exists ::env(OT_CLK_LEAF_SLEW_PS)] ? double($::env(OT_CLK_LEAF_SLEW_PS)) : 80.0}]
  set clr_n_skip_slew 0
  set clr_n_nets 0; set clr_n_bufs 0; set clr_worst_before 0.0; set clr_worst_after 0.0; set clr_seq 0
  for {set clr_pass 1} {$clr_pass <= $clr_passes + 1} {incr clr_pass} {
    set clr_todo {}
    set clr_worst 0.0
    if {$clr_slew_ps > 0} { estimate_parasitics -placement }
    foreach net [$clr_blk getNets] {
      if {![clr_is_clock_net $net]} continue
      set r [clr_net $net]
      if {$r eq ""} continue
      lassign $r drv loads
      lassign [clr_xy $drv] dx dy
      set far {}; set all_clk 1
      foreach it $loads {
        lassign [clr_lxy $it] lx ly
        set d [expr {double(abs($lx - $dx) + abs($ly - $dy)) / $clr_dbu}]
        if {$d > $clr_worst} { set clr_worst $d }
        if {$d > $clr_max_um} { lappend far [list $it $lx $ly $d] }
        if {![clr_is_clkcell [$it getInst]]} { set all_clk 0 }
      }
      set over_fo [expr {$clr_fo > 0 && $all_clk && [llength $loads] > $clr_fo}]
      if {$clr_slew_ps > 0 && ([llength $far] || $over_fo)} {
        # slew gate: worst placement-estimated load slew (ps, user time units)
        set ms 0.0
        foreach it $loads {
          set pp [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"]
          if {$pp eq "" || $pp eq "NULL"} continue
          set s [get_property $pp slew_max]
          if {$s > $ms} { set ms $s }
        }
        if {$ms <= $clr_slew_ps || (!$all_clk && $ms <= 2.0 * $clr_slew_ps)} {
          if {$clr_pass == 1} { incr clr_n_skip_slew }
          continue
        }
        # balanced siblings: every load of the net goes behind a repeater
        set far {}
        foreach it $loads {
          lassign [clr_lxy $it] lx ly
          lappend far [list $it $lx $ly [expr {double(abs($lx - $dx) + abs($ly - $dy)) / $clr_dbu}]]
        }
        puts [format "OT_CLK_LEAF_REPEAT pass %d net %s est slew %.1f ps > %.0f, %d loads" $clr_pass [$net getName] $ms $clr_slew_ps [llength $loads]]
        set over_fo 0
      }
      if {[llength $far] || $over_fo} { lappend clr_todo [list $net $drv $loads $far $over_fo] }
    }
    if {$clr_pass == 1} { set clr_worst_before $clr_worst }
    set clr_worst_after $clr_worst
    puts [format "OT_CLK_LEAF_REPEAT pass %d: %d nets over rule (max %.0f um, fanout %d, slew gate %.0f ps), worst load distance %.1f um" \
            $clr_pass [llength $clr_todo] $clr_max_um $clr_fo $clr_slew_ps $clr_worst]
    if {![llength $clr_todo] || $clr_pass > $clr_passes} break
    foreach job $clr_todo {
      lassign $job net drv loads far over_fo
      lassign [clr_xy $drv] dx dy
      # load groups: far loads (distance rule), else (fanout rule only) every load, farthest first
      if {![llength $far]} {
        foreach it $loads { lassign [clr_lxy $it] lx ly; lappend far [list $it $lx $ly [expr {double(abs($lx-$dx)+abs($ly-$dy))/$clr_dbu}]] }
      }
      set far [lsort -real -decreasing -index 3 $far]
      set cap [expr {$clr_fo > 0 ? $clr_fo : 1000000}]
      set groups {}
      while {[llength $far]} {
        set seed [lindex $far 0]; set g [list $seed]; set rest {}
        foreach f [lrange $far 1 end] {
          if {[llength $g] < $cap && (abs([lindex $f 1] - [lindex $seed 1]) + abs([lindex $f 2] - [lindex $seed 2])) <= $clr_max_um * $clr_dbu / 2.0} {
            lappend g $f
          } else { lappend rest $f }
        }
        lappend groups $g; set far $rest
      }
      # a fanout-only split keeps one group on the driver when that alone meets the cap
      if {![llength [lindex $job 3]] && [llength $groups] == 1} continue
      # slew mode: one group close to the driver gains nothing from a repeater
      if {$clr_slew_ps > 0 && [llength $groups] == 1 && [lindex [lindex [lindex $groups 0] 0] 3] <= $clr_max_um} continue
      set m [[$drv getMaster] getName]
      set cell [expr {[string match "BUF*" $m] ? $m : $clr_cell_default}]
      foreach g $groups {
        set sx 0.0; set sy 0.0; set pins {}
        foreach f $g {
          set it [lindex $f 0]
          lappend pins [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"]
          set sx [expr {$sx + [lindex $f 1]}]; set sy [expr {$sy + [lindex $f 2]}]
        }
        set cx [expr {$sx / [llength $g]}]; set cy [expr {$sy / [llength $g]}]
        set px [expr {(($dx + $cx) / 2.0) / $clr_dbu}]; set py [expr {(($dy + $cy) / 2.0) / $clr_dbu}]
        incr clr_seq
        set nm "clkleafrep_${clr_seq}"
        # STA pin objects (odb names carry escaped bus brackets; sta::find_pin takes the odb name as is)
        if {[llength $pins] > 1} {
          insert_buffer -buffer_cell $cell -net [sta::db_net_to_sta $net] -load_pins $pins -location [list $px $py] \
            -buffer_name $nm -net_name "clknet_${nm}"
        } else {
          insert_buffer -buffer_cell $cell -load_pins $pins -location [list $px $py] -buffer_name $nm -net_name "clknet_${nm}"
        }
        # the new net is the moved load's net (insert_buffer may uniquify -net_name, so findNet by name can miss it)
        set nn [[lindex [lindex $g 0] 0] getNet]
        if {$nn ne "NULL" && $nn ne ""} { $nn setSigType CLOCK }
        incr clr_n_bufs
      }
      incr clr_n_nets
    }
  }
  if {$clr_n_bufs} {
    detailed_placement {*}[clr_dpl_args]
    # KW-FIX-35-F 11-08 (FLOW class F, COORD 04:5x): one extra legalization when the plain check fails (same rule as
    # 20cff21bab, orfs_hold_mm OT_DPL_RESIDUAL).  KW-FIX-35-F2: that extra pass is the diamond legalizer (clr_dpl_args 1);
    # an ordinary second negotiation pass did not converge either (QC a10R 596 -> 604).  The mandatory check decides.
    if {[catch {check_placement}]} {
      puts "OT_DPL_RESIDUAL: CTS leaf-repeat check failed, legalization once more with [clr_dpl_args 1]"
      detailed_placement {*}[clr_dpl_args 1]
    }
    check_placement -verbose
  } elseif {[catch {check_placement}]} {
    # KW-FIX-35-F2: no repeater, but the stock CTS legalization (no check of its own when SKIP_CTS_REPAIR_TIMING=1)
    # left overlaps: repair them here, same diamond pass.  Repair only: the result is reported, the later stage checks
    # decide as before (no new gate).
    puts "OT_DPL_RESIDUAL: CTS check failed (no leaf repeater), legalization once more with [clr_dpl_args 1]"
    detailed_placement {*}[clr_dpl_args 1]
    puts "OT_DPL_RESIDUAL: CTS check after the extra legalization: [expr {[catch {check_placement}] ? "FAIL" : "PASS"}]"
  }
  puts [format "OT_CLK_LEAF_REPEAT done: %d nets repeated, %d repeaters, worst load distance %.1f -> %.1f um (%d nets over distance kept: est slew <= gate)" \
          $clr_n_nets $clr_n_bufs $clr_worst_before $clr_worst_after $clr_n_skip_slew]
}
}
if {$::ot_clr_run && $::ot_clr_mode eq "grt"} {
uplevel #0 {
  set clr_blk [ord::get_db_block]
  set clr_dbu [[ord::get_db_tech] getDbUnitsPerMicron]
  set clr_max_um [expr {[info exists ::env(OT_CLK_LEAF_MAX_UM)] ? double($::env(OT_CLK_LEAF_MAX_UM)) : 50.0}]
  set clr_fo [expr {[info exists ::env(OT_CLK_LEAF_MAX_FANOUT)] ? int($::env(OT_CLK_LEAF_MAX_FANOUT)) : 12}]
  set clr_cell_default [expr {[info exists ::env(OT_CLK_LEAF_CELL)] ? $::env(OT_CLK_LEAF_CELL) : "BUFx16f_ASAP7_75t_R"}]
  set clr_long_um [expr {[info exists ::env(OT_CLK_LEAF_LONG_UM)] ? double($::env(OT_CLK_LEAF_LONG_UM)) : 120.0}]
  set clr_gslew [expr {[info exists ::env(OT_CLK_LEAF_GRT_SLEW_PS)] ? double($::env(OT_CLK_LEAF_GRT_SLEW_PS)) : 150.0}]
  set clr_gpasses [expr {[info exists ::env(OT_CLK_LEAF_GRT_PASSES)] ? int($::env(OT_CLK_LEAF_GRT_PASSES)) : 3}]
  set clr_bal [expr {[info exists ::env(OT_CLK_LEAF_GRT_BAL)] && $::env(OT_CLK_LEAF_GRT_BAL) eq "1"}]
  set clr_chain_max [expr {[info exists ::env(OT_CLK_LEAF_GRT_CHAIN_MAX)] ? max(1, int($::env(OT_CLK_LEAF_GRT_CHAIN_MAX))) : 4}]
  set clr_rise [expr {[info exists ::env(OT_CLK_LEAF_GRT_RISE_PS)] ? double($::env(OT_CLK_LEAF_GRT_RISE_PS)) : 10.0}]
  set clr_drv [expr {[info exists ::env(OT_CLK_LEAF_GRT_DRV_PS)] ? double($::env(OT_CLK_LEAF_GRT_DRV_PS)) : 320.0}]
  array unset clr_g_done; array unset clr_g_rec
  set clr_g_order {}
  set clr_macros {}
  foreach clr_g_inst [$clr_blk getInsts] {
    if {[[$clr_g_inst getMaster] isBlock]} { set clr_g_b [$clr_g_inst getBBox]; lappend clr_macros [list $clr_g_inst [$clr_g_b xMin] [$clr_g_b yMin] [$clr_g_b xMax] [$clr_g_b yMax]] }
  }
  set clr_wl_file [file join [expr {[info exists ::env(OBJECTS_DIR)] && [file isdirectory $::env(OBJECTS_DIR)] ? $::env(OBJECTS_DIR) : "/tmp"}] "ot_clk_leaf_grt_wl.[pid].txt"]
  set clr_g_nets 0; set clr_g_bufs 0; set clr_g_skip 0; set clr_g_seq 0; set clr_g_worst 0.0
  for {set clr_pass 1} {$clr_pass <= $clr_gpasses + 1} {incr clr_pass} {
    set clr_cand {}
    foreach clr_g_net [$clr_blk getNets] {
      if {![clr_is_clock_net $clr_g_net]} continue
      if {$clr_bal && [info exists clr_g_done([$clr_g_net getName])]} continue
      set clr_g_r [clr_net $clr_g_net]
      if {$clr_g_r eq ""} continue
      lassign $clr_g_r clr_g_drv clr_g_loads
      set clr_g_all_clk 1
      foreach clr_g_it $clr_g_loads { if {![clr_is_clkcell [$clr_g_it getInst]]} { set clr_g_all_clk 0; break } }
      if {!$clr_g_all_clk && [llength $clr_g_loads] > 2} continue
      lappend clr_cand [list $clr_g_net $clr_g_drv $clr_g_loads]
    }
    # routed (global-route) wire length of every candidate: one report file (grt: <net> <wl um> <pins>)
    array unset clr_wl
    if {[llength $clr_cand]} {
      catch {suppress_message GRT 237}
      grt::create_wl_report_file $clr_wl_file 0
      foreach clr_g_c $clr_cand { grt::report_net_wire_length [lindex $clr_g_c 0] 1 0 0 $clr_wl_file }
      catch {unsuppress_message GRT 237}
      if {![catch {set clr_g_fh [open $clr_wl_file r]; set clr_g_txt [read $clr_g_fh]; close $clr_g_fh}]} {
        foreach clr_g_ln [split $clr_g_txt "\n"] {
          if {[regexp {^grt:\s+(\S+)\s+([0-9.eE+-]+)} $clr_g_ln -> clr_g_n clr_g_w]} { set clr_wl($clr_g_n) $clr_g_w }
        }
      }
      file delete -force $clr_wl_file
    }
    set clr_todo {}
    foreach clr_g_c $clr_cand {
      lassign $clr_g_c clr_g_net clr_g_drv clr_g_loads
      set clr_g_nm [$clr_g_net getName]
      if {![info exists clr_wl($clr_g_nm)]} continue
      set clr_g_wl $clr_wl($clr_g_nm)
      if {$clr_g_wl > $clr_g_worst} { set clr_g_worst $clr_g_wl }
      set clr_g_long [expr {$clr_long_um > 0 && $clr_g_wl > $clr_long_um}]
      set clr_g_cross 0
      if {!$clr_g_long && [llength $clr_macros] && $clr_g_wl > $clr_max_um} {
        set clr_g_own [list [$clr_g_drv getId]]
        foreach clr_g_it $clr_g_loads { lappend clr_g_own [[$clr_g_it getInst] getId] }
        foreach clr_g_g [$clr_g_net getGuides] {
          set clr_g_gb [$clr_g_g getBox]
          foreach clr_g_m $clr_macros {
            lassign $clr_g_m clr_g_mi clr_g_mx0 clr_g_my0 clr_g_mx1 clr_g_my1
            if {[$clr_g_gb xMax] > $clr_g_mx0 && [$clr_g_gb xMin] < $clr_g_mx1 && [$clr_g_gb yMax] > $clr_g_my0 && [$clr_g_gb yMin] < $clr_g_my1
                && [lsearch -exact $clr_g_own [$clr_g_mi getId]] < 0} { set clr_g_cross 1; break }
          }
          if {$clr_g_cross} break
        }
      }
      if {!$clr_g_long && !$clr_g_cross} continue
      set clr_g_ms 0.0
      foreach clr_g_it $clr_g_loads {
        set clr_g_pp [sta::find_pin "[[$clr_g_it getInst] getName]/[[$clr_g_it getMTerm] getName]"]
        if {$clr_g_pp eq "" || $clr_g_pp eq "NULL"} continue
        set clr_g_s [get_property $clr_g_pp slew_max]
        if {$clr_g_s > $clr_g_ms} { set clr_g_ms $clr_g_s }
      }
      if {$clr_gslew > 0 && $clr_g_ms <= $clr_gslew} { if {$clr_pass == 1} { incr clr_g_skip }; continue }
      puts [format "OT_CLK_LEAF_REPEAT grt pass %d net %s routed %.1f um%s, GRT est slew %.1f ps, %d loads" \
              $clr_pass $clr_g_nm $clr_g_wl [expr {$clr_g_cross ? " over a macro" : ""}] $clr_g_ms [llength $clr_g_loads]]
      lappend clr_todo [list $clr_g_net $clr_g_drv $clr_g_loads]
      if {$clr_bal} { set clr_g_rec($clr_g_nm) [list [clr_net_delay $clr_g_drv $clr_g_loads] $clr_g_ms {} $clr_g_drv] }
    }
    puts [format "OT_CLK_LEAF_REPEAT grt pass %d: %d of %d branch nets over rule (routed > %.0f um or over a macro, GRT slew gate %.0f ps)" \
            $clr_pass [llength $clr_todo] [llength $clr_cand] $clr_long_um $clr_gslew]
    if {![llength $clr_todo] || $clr_pass > $clr_gpasses} break
    global_route -start_incremental
    # the GRT stage process has not run detailed_placement yet: insert_buffer legalises through dpl (Opendp grid),
    # which segfaults uninitialised (OpenROAD 26Q3 pointOffMacro); this DPL builds the grid.
    # S81-COL-FLOW-1118 (DPL-0033 on S81 leaf t25_ns2 pilot and wave t51 a6): the design entering GRT is not always legal
    # (t51: 294 violations at this call, 36 left by the negotiation legalizer; t25: 2 BUFx6f overlaps), so the residual
    # survived into the repeater check.  Same overlap-aware policy as CTS: kit legalizer, then one diamond pass on a failed check.
    detailed_placement {*}[clr_dpl_args]
    if {[catch {check_placement}]} {
      puts "OT_DPL_RESIDUAL: GRT entry check failed, legalization once more with [clr_dpl_args 1]"
      detailed_placement {*}[clr_dpl_args 1]
    }
    foreach clr_g_job $clr_todo {
      lassign $clr_g_job clr_g_net clr_g_drv clr_g_loads
      lassign [clr_xy $clr_g_drv] clr_g_dx clr_g_dy
      set clr_g_far {}
      foreach clr_g_it $clr_g_loads { lassign [clr_lxy $clr_g_it] clr_g_lx clr_g_ly; lappend clr_g_far [list $clr_g_it $clr_g_lx $clr_g_ly [expr {double(abs($clr_g_lx-$clr_g_dx)+abs($clr_g_ly-$clr_g_dy))/$clr_dbu}]] }
      set clr_g_far [lsort -real -decreasing -index 3 $clr_g_far]
      set clr_g_cap [expr {$clr_fo > 0 ? $clr_fo : 1000000}]
      set clr_g_groups {}
      while {[llength $clr_g_far]} {
        set clr_g_seed [lindex $clr_g_far 0]; set clr_g_g [list $clr_g_seed]; set clr_g_rest {}
        foreach clr_g_f [lrange $clr_g_far 1 end] {
          if {[llength $clr_g_g] < $clr_g_cap && (abs([lindex $clr_g_f 1] - [lindex $clr_g_seed 1]) + abs([lindex $clr_g_f 2] - [lindex $clr_g_seed 2])) <= $clr_max_um * $clr_dbu / 2.0} {
            lappend clr_g_g $clr_g_f
          } else { lappend clr_g_rest $clr_g_f }
        }
        lappend clr_g_groups $clr_g_g; set clr_g_far $clr_g_rest
      }
      set clr_g_m [[$clr_g_drv getMaster] getName]
      set clr_g_cell [expr {[string match "BUF*" $clr_g_m] ? $clr_g_m : $clr_cell_default}]
      foreach clr_g_g $clr_g_groups {
        set clr_g_sx 0.0; set clr_g_sy 0.0; set clr_g_pins {}
        foreach clr_g_f $clr_g_g {
          set clr_g_it [lindex $clr_g_f 0]
          lappend clr_g_pins [sta::find_pin "[[$clr_g_it getInst] getName]/[[$clr_g_it getMTerm] getName]"]
          set clr_g_sx [expr {$clr_g_sx + [lindex $clr_g_f 1]}]; set clr_g_sy [expr {$clr_g_sy + [lindex $clr_g_f 2]}]
        }
        set clr_g_cx [expr {$clr_g_sx / [llength $clr_g_g]}]; set clr_g_cy [expr {$clr_g_sy / [llength $clr_g_g]}]
        # chain length: 1 (midpoint, the pass as before) or, balanced, k evenly spaced repeaters (each segment <= the long rule)
        set clr_g_k 1
        if {$clr_bal && $clr_long_um > 0} {
          set clr_g_d [expr {double(abs($clr_g_cx - $clr_g_dx) + abs($clr_g_cy - $clr_g_dy)) / $clr_dbu}]
          set clr_g_k [expr {min($clr_chain_max, max(1, int(ceil($clr_g_d / $clr_long_um)) - 1))}]
        }
        set clr_g_ldnet $clr_g_net
        for {set clr_g_j $clr_g_k} {$clr_g_j >= 1} {incr clr_g_j -1} {
          set clr_g_fr [expr {$clr_g_k == 1 ? 0.5 : double($clr_g_j) / ($clr_g_k + 1)}]
          set clr_g_px [expr {($clr_g_dx + ($clr_g_cx - $clr_g_dx) * $clr_g_fr) / $clr_dbu}]; set clr_g_py [expr {($clr_g_dy + ($clr_g_cy - $clr_g_dy) * $clr_g_fr) / $clr_dbu}]
          incr clr_g_seq
          set clr_g_bn "clkleafrepg_${clr_g_seq}"
          if {[llength $clr_g_pins] > 1} {
            insert_buffer -buffer_cell $clr_g_cell -net [sta::db_net_to_sta $clr_g_ldnet] -load_pins $clr_g_pins -location [list $clr_g_px $clr_g_py] \
              -buffer_name $clr_g_bn -net_name "clknet_${clr_g_bn}"
          } else {
            insert_buffer -buffer_cell $clr_g_cell -load_pins $clr_g_pins -location [list $clr_g_px $clr_g_py] -buffer_name $clr_g_bn -net_name "clknet_${clr_g_bn}"
          }
          if {$clr_g_j == $clr_g_k} {
            set clr_g_nn [[lindex [lindex $clr_g_g 0] 0] getNet]
          } else {
            set clr_g_nn [$clr_g_lastin getNet]
          }
          if {$clr_g_nn ne "NULL" && $clr_g_nn ne ""} { $clr_g_nn setSigType CLOCK; if {$clr_bal} { set clr_g_done([$clr_g_nn getName]) 1 } }
          incr clr_g_bufs
          if {$clr_bal} {
            # the new repeater = the driver of the moved load's net (insert_buffer may uniquify -buffer_name)
            set clr_g_bi ""
            if {$clr_g_nn ne "NULL" && $clr_g_nn ne ""} { foreach clr_g_t [$clr_g_nn getITerms] { if {[$clr_g_t isOutputSignal]} { set clr_g_bi [$clr_g_t getInst]; break } } }
            if {$clr_g_bi eq ""} { puts "OT_CLK_LEAF_REPEAT grt bal: repeater $clr_g_bn not found on its load net, chain stops"; break }
            set clr_g_nm0 [$clr_g_net getName]
            lset clr_g_rec($clr_g_nm0) 2 [concat [lindex $clr_g_rec($clr_g_nm0) 2] [list [$clr_g_bi getName]]]
          }
          if {$clr_g_j > 1} {
            # the next (upstream) repeater drives this one's input pin
            set clr_g_lastin ""
            foreach clr_g_t [$clr_g_bi getITerms] { if {[$clr_g_t isInputSignal] && [$clr_g_t getNet] ne "NULL"} { set clr_g_lastin $clr_g_t; break } }
            if {$clr_g_lastin eq ""} { puts "OT_CLK_LEAF_REPEAT grt bal: no input pin on [$clr_g_bi getName], chain stops at [expr {$clr_g_k - $clr_g_j + 1}] of $clr_g_k"; break }
            set clr_g_pins [list [sta::find_pin "[$clr_g_bi getName]/[[$clr_g_lastin getMTerm] getName]"]]
          }
        }
      }
      incr clr_g_nets
      if {$clr_bal} { set clr_g_done([$clr_g_net getName]) 1; lappend clr_g_order [$clr_g_net getName] }
    }
    # HEAD sd8g: GRT is a separate process and must apply the same overlap-aware
    # legalization policy as CTS before committing the incremental routing scene.
    detailed_placement {*}[clr_dpl_args]
    if {[catch {check_placement}]} {
      puts "OT_DPL_RESIDUAL: GRT leaf-repeat check failed, legalization once more with [clr_dpl_args 1]"
      detailed_placement {*}[clr_dpl_args 1]
    }
    check_placement -verbose
    global_route -end_incremental
    estimate_parasitics -global_routing
  }
  if {$clr_bal && $clr_g_bufs} { clr_bal_guard }
  if {$clr_g_bufs} { check_placement -verbose }
  puts [format "OT_CLK_LEAF_REPEAT grt done: %d nets repeated, %d repeaters (%d long / over-macro nets kept: GRT est slew <= gate), longest routed branch %.1f um" \
          $clr_g_nets $clr_g_bufs $clr_g_skip $clr_g_worst]
}
}
if {![info exists ::ot_clr_default] && $::ot_clr_mode eq "cts"
    && [info exists ::env(OT_CLR_NEXT_TCL)] && [string trim $::env(OT_CLR_NEXT_TCL)] ne ""
    && [file tail [string trim $::env(OT_CLR_NEXT_TCL)]] ne "clk_leaf_repeat.tcl"} {
  source [string trim $::env(OT_CLR_NEXT_TCL)]
}
