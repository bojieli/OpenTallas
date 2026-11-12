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
# CLK-LEAF-BAL-1 11-11 (DIE-HBM-100 / HBM-CORES-B b128_canon): the half-way rule above equalises DEPTH, not DELAY.  Every
# repeater takes the driver's master (BUFx24) whatever its load and wire, so a repeater on a long / loaded group costs
# ~59.8 ps and one on a short group ~37.8 ps (routed, FF).  b128_canon routed (RCX SPEF, FF): leaf arrivals of the
# repeaters under one leaf-clock level differ by up to 45 ps (median 19 ps over 16 families), and 157 reg-to-reg + 76
# port FF hold endpoints reopened (WNS -19.66 ps) after GRT hold repair had converged to 0; 65 of the 89 skew >= 15 ps
# paths have a clkleafrep stage on the diverging branch (pairs clkleafrep_367660 / _377661 are cousins: different
# parent nets, one common grandparent).
# OT_CLK_LEAF_REPEAT_BALANCE=1 (default OFF = byte-identical behaviour and output): BALANCED-BY-CONSTRUCTION SIZING.
#   Balance group = the clkleafrep repeaters whose parent net is driven from one common net (cousins + siblings: same
#   grandparent net; a repeater nested under another repeater is grouped with its siblings only).  Delay of a member =
#   mean propagated rising-edge clock arrival at its leaf loads (through nested repeaters), at the max and the min scene.
#   Target T = the mean leaf arrival of the whole level, un-repeated cousin leaf nets included (OT_CLK_LEAF_BAL_TARGET=
#   max: the slowest member, which lifts repeated subtrees above their un-repeated neighbours).  Every member faster
#   than T takes the clock buffer master (BUF* / HB* of its own name suffix = site / VT) whose leaf arrival comes
#   closest to T at BOTH scenes
#   (cost max(|dmax-Tmax|, |dmin-Tmin|)), never one whose worst load slew exceeds max(OT_CLK_LEAF_SLEW_PS or 80 ps, the
#   member's own slew before).  A weaker repeater spends in its own drive the delay its short / light group lacks in
#   wire RC.  Two rounds (sizes change the parent loads).  Position is not the lever: the Elmore delay of driver ->
#   repeater -> group is minimal near the midpoint and grows only quadratically off it, too little on short branches.
#   Runs in the CTS pass after the leaf repeaters are legal (placement RC, the kit's set_wire_rc); resized cells are
#   legalised again and the placement parasitics re-estimated.  NOT in the GRT pass: swaps there sit outside the
#   incremental-GRT window and ORFS repair_design then stops on EST-0104 (inconsistent parasitics state; b128_bal resume
#   11-12); measured on b128_canon the GRT-RC decision was neutral on the routed DB anyway (1 resize in the resume).
#   OT_CLK_LEAF_BAL_TOL_PS (default 3 ps): a member within it keeps its master.
#   Log lines: OT_CLK_LEAF_BALANCE ...  Measured with physical/common_flow/clk_leaf_sibling_report.tcl.
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
# ---- CLK-LEAF-BAL-1: delay-aware repeater sizing (OT_CLK_LEAF_REPEAT_BALANCE=1) ----
proc clr_bal_on {} {
  return [expr {[info exists ::env(OT_CLK_LEAF_REPEAT_BALANCE)] && [string trim $::env(OT_CLK_LEAF_REPEAT_BALANCE)] eq "1"}]
}
proc clr_is_rep {inst} { return [string match "clkleafrep*" [$inst getName]] }
# brings the arrival search up to date (a path iterator alone reads whatever is cached)
proc clr_sta_refresh {} { catch {worst_slack -max} }
# propagated clock arrival (ps, user units) of the RISING clock edge at an STA pin, the worst over the session scenes
# (max: latest, min: earliest), waveform edge removed; "" when the pin carries no clock arrival
proc clr_clk_arr {pin minmax} {
  set best ""
  foreach vertex [$pin vertices] {
    if {$vertex eq "NULL"} continue
    foreach rf {rise fall} {
      set paths [$vertex path_iterator $rf $minmax]
      while {[$paths has_next]} {
        set path [$paths next]; set tag [$path tag]
        if {[string first "(clock prop)" $tag] < 0 || [lindex $tag 4] ne "^"} continue
        set a [sta::time_sta_ui [$path arrival]]
        if {![string is double -strict $a]} continue
        set cl [get_clocks -quiet [lindex $tag 3]]
        if {[llength $cl]} { set a [expr {$a - [sta::time_sta_ui [lindex [[lindex $cl 0] waveform] 0]]}] }
        if {$best eq "" || ($minmax eq "max" ? $a > $best : $a < $best)} { set best $a }
      }
      $paths finish
    }
  }
  return $best
}
proc clr_out_net {inst} {
  foreach it [$inst getITerms] { if {[$it isOutputSignal]} { return [$it getNet] } }
  return NULL
}
proc clr_in_net {inst} {
  foreach it [$inst getITerms] { if {[$it isInputSignal] && [$it getNet] ne "NULL" && [$it getNet] ne ""} { return [$it getNet] } }
  return NULL
}
proc clr_net_drv {net} {
  foreach it [$net getITerms] { if {[$it isOutputSignal]} { return [$it getInst] } }
  return NULL
}
# leaf loads of a repeater (odb iterms), descending through nested clkleafrep repeaters
proc clr_rep_leaves {inst {depth 0}} {
  set on [clr_out_net $inst]
  if {$on eq "" || $on eq "NULL"} { return {} }
  set out {}
  foreach it [$on getITerms] {
    if {![$it isInputSignal]} continue
    set li [$it getInst]
    if {$depth < 8 && [clr_is_rep $li]} { lappend out {*}[clr_rep_leaves $li [expr {$depth + 1}]]; continue }
    lappend out $it
  }
  return $out
}
proc clr_sta_pin {it} { return [sta::find_pin "[[$it getInst] getName]/[[$it getMTerm] getName]"] }
# {mean leaf arrival max, mean leaf arrival min, worst slew on the repeater's own loads, n leaves} or ""
proc clr_rep_meas {inst} {
  set amax 0.0; set amin 0.0; set n 0
  foreach it [clr_rep_leaves $inst] {
    set pp [clr_sta_pin $it]
    if {$pp eq "" || $pp eq "NULL"} continue
    set a [clr_clk_arr $pp max]; set b [clr_clk_arr $pp min]
    if {$a eq "" || $b eq ""} continue
    set amax [expr {$amax + $a}]; set amin [expr {$amin + $b}]; incr n
  }
  if {!$n} { return "" }
  set smax 0.0
  foreach it [[clr_out_net $inst] getITerms] {
    if {![$it isInputSignal]} continue
    set pp [clr_sta_pin $it]
    if {$pp eq "" || $pp eq "NULL"} continue
    set s [get_property $pp slew_max]
    if {$s > $smax} { set smax $s }
  }
  return [list [expr {$amax / $n}] [expr {$amin / $n}] $smax $n]
}
# clock buffer masters of the repeater's own family: BUF* / HB* with the same name suffix (site / VT), in the liberty
proc clr_bal_masters {master} {
  if {[info exists ::clr_bal_mcache($master)]} { return $::clr_bal_mcache($master) }
  set out {}
  if {[regexp {^(?:BUF|HB)[^_]*(_.*)$} $master -> sfx]} {
    foreach lib [[ord::get_db] getLibs] {
      foreach m [$lib getMasters] {
        set nm [$m getName]
        if {![regexp {^(?:BUF|HB)[^_]*(_.*)$} $nm -> s2] || $s2 ne $sfx} continue
        if {![llength [get_lib_cells -quiet */$nm]]} continue
        lappend out $m
      }
    }
  }
  set ::clr_bal_mcache($master) $out
  return $out
}
# balance groups from the DB: {key {repeater names}} ...; outer groups first, nested ones (parent driven by a repeater) last
proc clr_bal_groups {} {
  set blk [ord::get_db_block]
  set keys {}; array set grp {}; array set nested {}
  foreach i [$blk getInsts] {
    if {![clr_is_rep $i]} continue
    set pn [clr_in_net $i]
    if {$pn eq "NULL"} continue
    set d [clr_net_drv $pn]; set key [$pn getName]; set lvl [$pn getName]
    if {$d ne "NULL" && [clr_is_rep $d]} {
      set nested($key) 1
    } elseif {$d ne "NULL"} {
      set gn [clr_in_net $d]
      if {$gn ne "NULL"} { set key "[$gn getName] (grandparent)"; set lvl [$gn getName] }
    }
    if {![info exists grp($key)]} { lappend keys $key; set lnet($key) $lvl }
    lappend grp($key) [$i getName]
  }
  set outer {}; set inner {}
  foreach k $keys {
    if {[info exists nested($k)]} { lappend inner [list $k $grp($k) $lnet($k) 1] } else { lappend outer [list $k $grp($k) $lnet($k) 0] }
  }
  return [concat $outer $inner]
}
# every leaf of one balance level (odb iterms): nested group = the loads of the repeater-driven parent net; outer group =
# the loads of every clock-buffer net fed from the grandparent net, repeated or NOT (the un-repeated cousin leaf nets
# set the level's insertion too), through the clkleafrep repeaters
proc clr_level_leaves {lnet nested} {
  set out {}
  if {$nested} { set nets [list $lnet] } else {
    set nets {}
    foreach it [$lnet getITerms] {
      if {![$it isInputSignal] || ![clr_is_clkcell [$it getInst]]} continue
      set on [clr_out_net [$it getInst]]
      if {$on ne "NULL" && $on ne ""} { lappend nets $on }
    }
  }
  foreach n $nets {
    foreach it [$n getITerms] {
      if {![$it isInputSignal]} continue
      if {[clr_is_rep [$it getInst]]} { lappend out {*}[clr_rep_leaves [$it getInst]] } else { lappend out $it }
    }
  }
  return $out
}
# balance target {Tmax Tmin} of a group: OT_CLK_LEAF_BAL_TARGET=mean (default) = the mean leaf arrival of the whole
# level (clr_level_leaves); max = the slowest member (equalises the repeaters among themselves but lifts a repeated
# subtree above its un-repeated neighbours: b128_canon routed, that moved the worst hold to the tree top, -44.8 ps)
proc clr_level_target {g} {
  set mode [expr {[info exists ::env(OT_CLK_LEAF_BAL_TARGET)] ? [string trim $::env(OT_CLK_LEAF_BAL_TARGET)] : "mean"}]
  if {$mode ne "mean" || [llength $g] < 4} { return "" }
  set ln [[ord::get_db_block] findNet [lindex $g 2]]
  if {$ln eq "" || $ln eq "NULL"} { return "" }
  set amax 0.0; set amin 0.0; set n 0
  foreach it [clr_level_leaves $ln [lindex $g 3]] {
    set pp [clr_sta_pin $it]
    if {$pp eq "" || $pp eq "NULL"} continue
    set a [clr_clk_arr $pp max]; set b [clr_clk_arr $pp min]
    if {$a eq "" || $b eq ""} continue
    set amax [expr {$amax + $a}]; set amin [expr {$amin + $b}]; incr n
  }
  if {!$n} { return "" }
  return [list [expr {$amax / $n}] [expr {$amin / $n}]]
}
# re-estimates the parasitics after master swaps.  An odb swapMaster DROPS the estimated parasitics of the touched nets
# (b128_canon 4_cts, placement RC: clkleafrep_367660 leaf arrival 219.7 ps -> swap to BUFx2 and back -> 202.1 ps until
# re-estimated; routed SPEF parasitics survive a swap).  cts: placement estimate, grt: GRT estimate, else
# ::clr_bal_reest_cmd when set (the report tool), else nothing.
proc clr_bal_reest {stage} {
  if {$stage eq "cts"} { estimate_parasitics -placement
  } elseif {$stage eq "grt"} { estimate_parasitics -global_routing
  } elseif {[info exists ::clr_bal_reest_cmd] && $::clr_bal_reest_cmd ne ""} { uplevel #0 $::clr_bal_reest_cmd }
  clr_sta_refresh
}
# groups: clr_bal_groups.  Two rounds; each round measures every group, then evaluates the candidate masters in BATCH
# (all members that may take master c are swapped to c together, one re-estimate, every member measured: members of
# different groups do not interact, siblings only through the parent load, which round 2 corrects), and gives each
# member its best admissible master.  Returns the number of repeaters whose master changed.
proc clr_balance {groups stage} {
  set tol [expr {[info exists ::env(OT_CLK_LEAF_BAL_TOL_PS)] ? double($::env(OT_CLK_LEAF_BAL_TOL_PS)) : 3.0}]
  set slim 80.0
  if {[info exists ::env(OT_CLK_LEAF_SLEW_PS)] && double($::env(OT_CLK_LEAF_SLEW_PS)) > 0} { set slim [expr {double($::env(OT_CLK_LEAF_SLEW_PS))}] }
  set blk [ord::get_db_block]
  # arrivals need the propagated (real) tree; ideal clocks are propagated for the measurement and restored after
  set ideal {}
  foreach c [all_clocks] { if {[llength [get_property $c sources]] && ![get_property $c is_propagated]} { lappend ideal $c } }
  if {[llength $ideal]} { set_propagated_clock $ideal }
  array set orig {}
  set ngrp 0; set wb 0.0; set wa 0.0
  for {set rnd 1} {$rnd <= 2} {incr rnd} {
    clr_bal_reest $stage
    set todo {}
    foreach g [lreverse $groups] {
      set rows {}
      foreach nm [lindex $g 1] {
        set i [$blk findInst $nm]
        if {$i eq "" || $i eq "NULL"} continue
        set m [clr_rep_meas $i]
        if {$m ne ""} { lappend rows [list $i {*}$m] }
      }
      if {[llength $rows] < 2} continue
      set rows [lsort -real -decreasing -index 1 $rows]
      if {$rnd == 1} { incr ngrp; set wb [expr {max($wb, [lindex [lindex $rows 0] 1] - [lindex [lindex $rows end] 1])}] }
      set tg [clr_level_target $g]
      if {$tg ne ""} { lassign $tg tmax tmin; set mem $rows } else { lassign [lindex $rows 0] - tmax tmin; set mem [lrange $rows 1 end] }
      foreach row $mem {
        lassign $row i d0max d0min s0
        set cost0 [expr {max(abs($d0max - $tmax), abs($d0min - $tmin))}]
        # sizing only slows a member down: one at or above the target keeps its master
        if {$cost0 <= $tol || $d0max >= $tmax} continue
        if {![info exists orig($i)]} { set orig($i) [$i getMaster] }
        lappend todo [list $i [$i getMaster] $tmax $tmin [expr {max($slim, $s0)}] $cost0 $d0max $d0min]
      }
    }
    if {![llength $todo]} break
    set cands {}
    foreach t $todo { foreach cm [clr_bal_masters [[lindex $t 1] getName]] { if {[lsearch -exact $cands $cm] < 0} { lappend cands $cm } } }
    array unset best; array unset bestc
    foreach t $todo { set best([lindex $t 0]) [lindex $t 1]; set bestc([lindex $t 0]) [lindex $t 5] }
    foreach cm $cands {
      set sw {}
      foreach t $todo {
        lassign $t i m0
        if {$cm eq $m0 || [lsearch -exact [clr_bal_masters [$m0 getName]] $cm] < 0} continue
        $i swapMaster $cm; lappend sw $t
      }
      if {![llength $sw]} continue
      clr_bal_reest $stage
      foreach t $sw {
        lassign $t i m0 tmax tmin lim
        set mm [clr_rep_meas $i]
        if {$mm eq ""} continue
        lassign $mm dmax dmin smax
        set c [expr {max(abs($dmax - $tmax), abs($dmin - $tmin))}]
        if {$smax <= $lim && $c < $bestc($i)} { set best($i) $cm; set bestc($i) $c }
      }
    }
    foreach t $todo {
      lassign $t i m0 tmax tmin lim cost0 d0max d0min
      if {[$i getMaster] ne $best($i)} { $i swapMaster $best($i) }
      if {$best($i) ne $m0} {
        puts [format "OT_CLK_LEAF_BALANCE %s round %d %s %s -> %s: leaf arrival %.1f/%.1f ps vs target %.1f/%.1f (max/min), cost %.1f -> %.1f ps" \
                $stage $rnd [$i getName] [$m0 getName] [$best($i) getName] $d0max $d0min $tmax $tmin $cost0 $bestc($i)]
      }
    }
  }
  clr_bal_reest $stage
  set nsw 0
  foreach i [array names orig] { if {[$i getMaster] ne $orig($i)} { incr nsw } }
  foreach g $groups {
    set v {}
    foreach nm [lindex $g 1] {
      set i [$blk findInst $nm]
      if {$i eq "" || $i eq "NULL"} continue
      set m [clr_rep_meas $i]; if {$m ne ""} { lappend v [lindex $m 0] }
    }
    if {[llength $v] >= 2} { set wa [expr {max($wa, [tcl::mathfunc::max {*}$v] - [tcl::mathfunc::min {*}$v])}] }
  }
  puts [format "OT_CLK_LEAF_BALANCE %s done: %d groups, %d repeaters resized, worst group leaf-arrival spread (max scene) %.1f -> %.1f ps (tol %.1f, slew limit %.0f ps)" \
          $stage $ngrp $nsw $wb $wa $tol $slim]
  if {[llength $ideal]} { unset_propagated_clock $ideal }
  return $nsw
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
    # CLK-LEAF-BAL-1 (a): delay-aware sizing on the legal tree, then the resized cells are legalised again
    if {[clr_bal_on]} {
      if {[clr_balance [clr_bal_groups] cts]} {
        detailed_placement {*}[clr_dpl_args]
        if {[catch {check_placement}]} {
          puts "OT_DPL_RESIDUAL: CTS leaf-balance check failed, legalization once more with [clr_dpl_args 1]"
          detailed_placement {*}[clr_dpl_args 1]
        }
        check_placement -verbose
        estimate_parasitics -placement
      }
    }
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
    }
    puts [format "OT_CLK_LEAF_REPEAT grt pass %d: %d of %d branch nets over rule (routed > %.0f um or over a macro, GRT slew gate %.0f ps)" \
            $clr_pass [llength $clr_todo] [llength $clr_cand] $clr_long_um $clr_gslew]
    if {![llength $clr_todo] || $clr_pass > $clr_gpasses} break
    global_route -start_incremental
    # the GRT stage process has not run detailed_placement yet: insert_buffer legalises through dpl (Opendp grid),
    # which segfaults uninitialised (OpenROAD 26Q3 pointOffMacro); the design is legal, so this DPL only builds the grid
    detailed_placement
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
        set clr_g_px [expr {(($clr_g_dx + $clr_g_cx) / 2.0) / $clr_dbu}]; set clr_g_py [expr {(($clr_g_dy + $clr_g_cy) / 2.0) / $clr_dbu}]
        incr clr_g_seq
        set clr_g_bn "clkleafrepg_${clr_g_seq}"
        if {[llength $clr_g_pins] > 1} {
          insert_buffer -buffer_cell $clr_g_cell -net [sta::db_net_to_sta $clr_g_net] -load_pins $clr_g_pins -location [list $clr_g_px $clr_g_py] \
            -buffer_name $clr_g_bn -net_name "clknet_${clr_g_bn}"
        } else {
          insert_buffer -buffer_cell $clr_g_cell -load_pins $clr_g_pins -location [list $clr_g_px $clr_g_py] -buffer_name $clr_g_bn -net_name "clknet_${clr_g_bn}"
        }
        set clr_g_nn [[lindex [lindex $clr_g_g 0] 0] getNet]
        if {$clr_g_nn ne "NULL" && $clr_g_nn ne ""} { $clr_g_nn setSigType CLOCK }
        incr clr_g_bufs
      }
      incr clr_g_nets
    }
    detailed_placement
    global_route -end_incremental
    estimate_parasitics -global_routing
  }
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
