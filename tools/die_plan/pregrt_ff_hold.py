#!/usr/bin/env python3
"""R-CLOCK HOLD BUILD (HOLD-TAP-1 11-13, RULEBOOK-1113 R-CLOCK; extends HEAD-TILE-PREGRT-HOLD DH59-TILE 11-03).

Every gen_phys kit repairs its FF hold debt ONCE, on the tap-balanced post-CTS database (4_cts.odb), on placement
parasitics, before the first global route.  OPT-IN per type (COORD 11-13 07:2x ruling on merge train 44, default-
preserving): plan clock.pregrt_ff_hold true turns it on; absent or false = no tcl and no config line, as before this
rule.  Turning it on per die follows a signed proof and the die owner's plan event.

Why (measured 11-13, same kits that ended HOLD_STRUCTURAL / time cap at GRT):
  - The hold debt of a kit is a CONTRACT quantity known as soon as the tap trees are balanced: a cross-tap register
    pair pays the launch port's tap window W_p (gen_phys.tap_window_tcl: -source -early -W_p, no CRPR across ports)
    + 25 ps hold uncertainty + the residual tree mismatch; an input port pays the seam contract in_min.  QC
    sle_st_a_v1: 9,104 reg-to-reg violators, 8,668 of them cross-tap (median -14.5 ps, median distance 11 um).
    S81 slice_station t41: 7,049 violators, 13 reg-to-reg, the rest input-port contract.  HEAD hd_turn_b: 2,312 = 34 + 2,278.
  - It is NOT a tap insertion mismatch: 4_cts_final.rpt is written BEFORE cts_post.tcl (tap_balance), so its
    120-185 ps launch/capture difference is the unbalanced tree.  After the balance the tap means sit within the window.
  - The in-flow GRT repair re-routes per buffer (QC sle_st_a: 1,384 buffers in 9,432 s; hd_spn_end 3,809 in 5.2 h)
    and ends on the 3 h stall guard; on placement parasitics the same work is minutes (hd_tile 24,282 buffers, 166 s).
What changed against the 11-03 opt-in form:
  1. opt-in (enabled(), COORD 11-13 07:2x); the run_kit.sh step is advisory: any failure keeps 4_cts.odb and the GRT
     repair as before, and prints one classified PREGRT_HOLD_FALLBACK line (run_<goal>.log) that autopilot records;
  2. TWO scenes when run_kit.sh passes TLIBS (TC_LIB_FILES): TC/mode tt checks setup, BC/mode ff checks hold, so
     repair_timing never spends TT setup slack on a hold cell (the FF-only form could only see FF setup);
  3. ROUTE GUARD on CROSS-TAP pairs only: built to +OT_PREGRT_HOLD_GUARD ps (plan clock.pregrt_hold_guard_ps,
     default 45).  Measured on the hd_turn_b proof, placement -> routed hold loss per pair: cross-tap median -0.9,
     p90 11.5, p99 26.5 ps (571 pairs); same-tap p99 11.0 (3,300 pairs).  Before the rule the GRT repair closed the
     cross-tap u_ft_t_s0 -> u_ft_t_s1 hops to +0.45 and route took them to -14.07 (25 endpoints); with the guard at
     45 the same hops route at >= +17.0.  Ports and same-tap pairs are built to OT_PREGRT_HOLD_PORT_MARGIN (5;
     routed same-tap worst +6.75): a uniform guard pads the ordinary zero-logic pairs of the whole kit and spends
     setup (see the TAIL comment).  NOT covered by any placement-basis guard: an unpadded long hop whose data wire
     the placement estimate over-states (hd_turn_b u_srl_10 -> u_rrl_11: +50.2 placed, +8.7 at GRT, +3.0 routed);
     the in-flow GRT repair sees those on GRT parasitics;
  4. the clock network and every clock sink are FIRM while hold cells are legalized (tap balance stays as measured);
  5. a class line before / after (port_in / same_tap / cross_tap / port_out) and pregrt_ff_hold_open.tsv = the
     endpoints the build could not close (ESCALATE: lockup latch / same tap / +1 cycle are plan forms);
  6. fail-safe (pg_verdict, HOLD-GRT-1: setup rejects only below the -42 ps gate AND > 5 ps below the floor): a TT setup loss, no hold gain or a tool error writes nothing (OT_PREGRT_FF_HOLD FALLBACK).
The in-flow GRT FF repair stays and takes the residual; sign-off FF hold >= 0 stays the only gate.  Timing context =
hold_gate.tcl verbatim (same contract, same overlay), so the kit carries the head of its own hold_gate.tcl."""
import os
from pathlib import Path

MARK = "# A separate FF-only process: do not impersonate the shared multi-mode context.\n"
CONFIG = "export OT_PREGRT_FF_HOLD = 1"
GUARD_PS = 45.0
# the single-scene read of hold_gate.tcl; replaced (exactly once, fail closed) by the two-scene read below
READ = ("foreach l $::env(PLIBS) { read_liberty $l }\n"
        "read_db $::env(ODB)\n"
        "read_sdc $::env(SDC)\n"
        "set_propagated_clock [all_clocks]\n")
READ2 = r"""# R-CLOCK HOLD BUILD: TLIBS (TC_LIB_FILES) given -> scene TC / mode tt (setup) + scene BC / mode ff (hold); the
# overlay below is applied in mode ff.  No TLIBS (a runner older than the rule): the FF-only read of hold_gate.tcl.
set pg_two [expr {[info exists ::env(TLIBS)] && [llength $::env(TLIBS)]}]
if {$pg_two} {
  foreach l [concat $::env(TLIBS) $::env(PLIBS)] { read_liberty $l }
  set_mode tt
  set_mode ff
  define_scene TC -mode tt -liberty $::env(TLIBS)
  define_scene BC -mode ff -liberty $::env(PLIBS)
  read_db $::env(ODB)
  read_sdc -mode tt $::env(SDC)
  read_sdc -mode ff $::env(SDC)
  set_mode tt
  set_propagated_clock [all_clocks]
  set_false_path -hold -from [all_clocks]
  set_mode ff
  set_propagated_clock [all_clocks]
  set_false_path -setup -from [all_clocks]
} else {
  foreach l $::env(PLIBS) { read_liberty $l }
  read_db $::env(ODB)
  read_sdc $::env(SDC)
  set_propagated_clock [all_clocks]
}
"""
TAIL = r"""# R-CLOCK HOLD BUILD: repair + legalize on the context above, then replace 4_cts.odb (fail-safe: FALLBACK writes nothing)
set pg_guard [expr {[info exists ::env(OT_PREGRT_HOLD_GUARD)] && [string is double -strict $::env(OT_PREGRT_HOLD_GUARD)] ? $::env(OT_PREGRT_HOLD_GUARD) : 45.0}]
set pg_blk [ord::get_db_block]
# FIX-HOLDSTALL 11-14 AUTO: the build runs only when the kit has >= AUTO_MIN register-to-register FF hold violators (a real
# internal debt the in-flow GRT repair would grind through for hours); fewer, or port-only hold (advisory), leave 4_cts.odb
# untouched and rc 0.  AUTO_MIN is baked in at install (-1 = plan opt-in, always runs).
set pg_auto @PG_AUTO_MIN@
if {$pg_auto >= 0} {
  set pg_nrr -1
  if {[catch {
    set pg_ck [all_registers -clock_pins]; set pg_dp [all_registers -data_pins]
    set pg_rrp [find_timing_paths -path_delay min -from $pg_ck -to $pg_dp -group_path_count 1000000 -endpoint_path_count 1 -slack_max 0]
    set pg_nrr [llength $pg_rrp]
  } pg_err]} { puts "OT_PREGRT_FF_HOLD AUTO: register-to-register count unavailable ($pg_err); the build runs"; set pg_nrr $pg_auto }
  if {$pg_nrr < $pg_auto} {
    puts "OT_PREGRT_FF_HOLD AUTO skip: $pg_nrr register-to-register hold violators < $pg_auto (port-only hold is advisory; the in-flow GRT repair takes the rest)"
    exit 0
  }
  puts "OT_PREGRT_FF_HOLD AUTO run: $pg_nrr register-to-register hold violators >= $pg_auto"
}
# HOLD-GRT-1 11-14 ACCEPT TEST.  Setup is a reason to discard the repair only when the repair breached the R-MINIMAL gate
# (TT setup < OT_PREGRT_SETUP_GATE, default -42 ps) AND moved the placement-estimate WNS by more than OT_PREGRT_SETUP_TOL (5 ps)
# below the pre-repair floor min(s0, 0).  The old test (any loss > 1 ps) threw away every repair on a kit whose placement-estimate
# WNS is already far below the gate (hc0 -515.45 -> -518.27, stm_v1 -8.12 -> -9.62): a worst path no hold cell sits on moves a
# few ps with every legalized cell, and the GRT setup repair owns that term.  Hold: a gain of >= 1 ps on a kit with hold debt.
# Returns "" (accept) or the FALLBACK reason.
proc pg_verdict {w0 w1 n0 s0 s1 {n1 -1} {t0 0.0} {t1 0.0}} {
  set gate -42.0; set tol 5.0
  if {[info exists ::env(OT_PREGRT_SETUP_GATE)] && [string is double -strict $::env(OT_PREGRT_SETUP_GATE)]} { set gate $::env(OT_PREGRT_SETUP_GATE) }
  if {[info exists ::env(OT_PREGRT_SETUP_TOL)] && [string is double -strict $::env(OT_PREGRT_SETUP_TOL)]} { set tol $::env(OT_PREGRT_SETUP_TOL) }
  if {$s1 < $gate && $s1 < [expr {min($s0, 0.0) - $tol}]} { return [format "TT setup loss %.2f -> %.2f (gate %.1f, tol %.1f)" $s0 $s1 $gate $tol] }
  # QC-MCLK lever 3 11-16 (cbn_q01: endpoints 21,467 -> 2,707, TNS -1.26 us -> -78 ns, discarded because one latch endpoint kept
  # the WNS): fewer violating endpoints with a better TNS is a gain even when the worst endpoint did not move.
  if {$w1 < $w0 + 1.0 && $n0 > 0 && !($n1 >= 0 && $n1 < $n0 && $t1 > $t0)} { return [format "no hold gain %.2f -> %.2f (endpoints %d -> %d)" $w0 $w1 $n0 $n1] }
  return ""
}
proc pg_hold {} { return [sta::time_sta_ui [sta::worst_slack_cmd min]] }
proc pg_tns {} { return [sta::time_sta_ui [sta::total_negative_slack_cmd min]] }
proc pg_setup {} { return [sta::time_sta_ui [sta::worst_slack_cmd max]] }
# tap port of a clock pin: drivers followed back through the tree to the block terminal (cached per net)
set pg_tapc [dict create]
proc pg_tap_of {it} {
  global pg_tapc
  set net [$it getNet]; set chain {}; set r "?"
  for {set h 0} {$h < 400 && $net ne "NULL" && $net ne ""} {incr h} {
    set nn [$net getName]
    if {[dict exists $pg_tapc $nn]} { set r [dict get $pg_tapc $nn]; break }
    lappend chain $nn
    set bts [$net getBTerms]
    if {[llength $bts]} { set r [[lindex $bts 0] getName]; break }
    set drv ""
    foreach t [$net getITerms] { if {[$t isOutputSignal]} { set drv $t; break } }
    if {$drv eq ""} break
    set net "NULL"
    foreach t [[$drv getInst] getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL"} { set net [$t getNet]; break } }
  }
  foreach c $chain { dict set pg_tapc $c $r }
  return $r
}
proc pg_clk_iterm {inst} {
  foreach t [$inst getITerms] { if {[$t isInputSignal] && [$t getNet] ne "NULL" && [[$t getNet] getSigType] eq "CLOCK"} { return $t } }
  return ""
}
# every FF hold violating endpoint by class; open != "" also writes the list (worst first, at most 5000 rows)
proc pg_classes {when {open ""}} {
  set cls {port_in same_tap cross_tap port_out}
  foreach c $cls { set n($c) 0; set w($c) 0.0 }
  set rows {}
  if {[catch {set ps [find_timing_paths -path_delay min -group_path_count 3000000 -endpoint_path_count 1 -slack_max 0]} err]} {
    puts "OT_PREGRT_FF_HOLD class $when unavailable ($err)"; return
  }
  foreach pe $ps {
    set s [sta::time_sta_ui [$pe slack]]
    set a [sta::sta_to_db_pin [get_property $pe startpoint]]; set b [sta::sta_to_db_pin [get_property $pe endpoint]]
    set lt "-"; set ct "-"
    if {$a eq "NULL" || $a eq ""} { set c port_in
    } elseif {$b eq "NULL" || $b eq ""} { set c port_out
    } else {
      set li [pg_clk_iterm [$a getInst]]
      set lt [expr {$li eq "" ? "?" : [pg_tap_of $li]}]
      set ci [pg_clk_iterm [$b getInst]]
      set ct [expr {$ci eq "" ? "?" : [pg_tap_of $ci]}]
      set c [expr {$lt eq $ct ? "same_tap" : "cross_tap"}]
    }
    incr n($c); if {$s < $w($c)} { set w($c) $s }
    if {$open ne ""} { lappend rows [list $s $c [get_full_name [get_property $pe startpoint]] [get_full_name [get_property $pe endpoint]] $lt $ct] }
  }
  set line "OT_PREGRT_FF_HOLD class $when"
  foreach c $cls { append line [format " %s %d ws %.2f" $c $n($c) $w($c)] }
  puts $line
  if {$open ne ""} {
    set f [open $open w]; puts $f "slack_ps\tclass\tstart\tend\tlaunch_tap\tcapture_tap"
    foreach r [lrange [lsort -real -index 0 $rows] 0 4999] { puts $f [join $r "\t"] }
    close $f
  }
}
if {[file exists /work/hold_sdc_guard.tcl]} { source /work/hold_sdc_guard.tcl }   ;# HOLD-SDC-1116
set pg_w0 [pg_hold]; set pg_n0 [sta::endpoint_violation_count min]; set pg_s0 [pg_setup]; set pg_tn0 [pg_tns]
set pg_i0 [llength [$pg_blk getInsts]]; set pg_t0 [clock seconds]
puts "OT_PREGRT_FF_HOLD before wns $pg_w0 endpoints $pg_n0 insts $pg_i0 setup_wns $pg_s0 scenes [expr {$pg_two ? {TC+BC} : {BC only (no TLIBS: setup guard at FF)}}] guard $pg_guard"
pg_classes before
# the clock network and its sinks keep their sites: FIRM while hold cells are seated and legalized
set pg_lock {}
foreach pg_net [$pg_blk getNets] {
  if {[$pg_net getSigType] ne "CLOCK"} continue
  foreach pg_it [$pg_net getITerms] {
    set pg_i [$pg_it getInst]
    if {[$pg_i getPlacementStatus] eq "PLACED"} { lappend pg_lock $pg_i; $pg_i setPlacementStatus FIRM }
  }
}
set pg_fail ""; set pg_xt "nan"
# tap window ports of the kit SDC (gen_phys.tap_window_tcl: set_clock_latency -source -early -clock <ck> <-W_p>
# [get_ports {...}]): port -> {clock early}.  Early core-tap ports with an FF overlay (core_taps_ff.sdc) keep their
# FF value untouched (no cross-tap guard on them).
set pg_taps [dict create]
if {[info exists hg_txt]} {
  set pg_skip {}
  set pg_cf [file join [file dirname $hg_gold] core_taps_ff.sdc]
  if {[file exists $pg_cf]} {
    set pg_f [open $pg_cf]
    foreach pg_l [split [read $pg_f] "\n"] { if {[regexp {\[get_ports \{?([^\}\]]+)\}?\]} $pg_l -> pg_pl]} { foreach pg_p $pg_pl { lappend pg_skip $pg_p } } }
    close $pg_f
  }
  foreach pg_l [split $hg_txt "\n"] {
    if {![regexp {^set_clock_latency -source -early -clock (\S+) (-?[0-9.]+) \[get_ports \{?([^\}\]]+)\}?\]\s*$} $pg_l -> pg_ck pg_e pg_pl]} continue
    foreach pg_p $pg_pl { if {$pg_p ni $pg_skip && [llength [get_ports -quiet $pg_p]]} { dict set pg_taps $pg_p [list $pg_ck $pg_e] } }
  }
}
set pg_pm [expr {[info exists ::env(OT_PREGRT_HOLD_PORT_MARGIN)] && [string is double -strict $::env(OT_PREGRT_HOLD_PORT_MARGIN)] ? $::env(OT_PREGRT_HOLD_PORT_MARGIN) : 5.0}]
set pg_in [all_inputs -no_clocks]; set pg_out [all_outputs]
set pg_dg [expr {$pg_guard - $pg_pm}]
# PREGRT-NONPORT 11-18 (COORD): same scope as the GRT repair (grt_nonport_hold.tcl): hold from input ports is excepted.  The kit SDC
# launches port data early by construction (set_input_delay -min -135 on a 250 ps vclk vs ~300 ps capture insertion), so a port_in hold pad
# (4-12k cells on the sc family) only spends setup; R-MINIMAL gates internal FF hold and port-boundary hold is a die-level check.
# OT_PREGRT_HOLD_PORTS=1 restores the old all-paths behaviour.
set pg_np_scope [expr {![info exists ::env(OT_PREGRT_HOLD_PORTS)] || $::env(OT_PREGRT_HOLD_PORTS) ne "1"}]
proc pg_np_apply {} { if {$::pg_np_scope && [llength $::pg_in]} { set_false_path -hold -from $::pg_in } }
proc pg_np_end {} { if {$::pg_np_scope && ![info exists ::pg_scope_sdc] && [llength $::pg_in]} { unset_path_exceptions -hold -from $::pg_in } }
pg_np_apply
# HOLD-MARGIN-FAMILY 11-17: extra REG-TO-REG pass to OT_PREGRT_HOLD_R2R_MARGIN (die family value, 0 = off); ports excepted, so the port seam
# margin above is unchanged.  Same fail-safe as the rest of the build (TT setup is judged after the whole build, pg_verdict).
set pg_rm [expr {[info exists ::env(OT_PREGRT_HOLD_R2R_MARGIN)] && [string is double -strict $::env(OT_PREGRT_HOLD_R2R_MARGIN)] ? $::env(OT_PREGRT_HOLD_R2R_MARGIN) : 0.0}]
if {[catch {
  # (A) every hold path, ports included, to the base margin (OT_PREGRT_HOLD_PORT_MARGIN, 5): the seam contract
  #     (in_min / out_min) and same-tap pairs are padded as the GRT repair would pad them, with no route guard: port
  #     hold is judged at die STA against the real arrivals of the parent, and a same-tap pair keeps its CRPR credit
  #     at route (before the rule the routed misses were cross-tap only).  A uniform guard above ~25 ps pads the
  #     ordinary zero-logic pairs of the whole kit (hd_turn_b: 1,014 cells at 25, 2,678 at 28, 3,319 at 35, TT setup
  #     104 -> 43).
  # (B) CROSS-TAP pairs only, to the route guard: port hold is excepted and the early source latency of every tap
  #     port (the kit tap window W_p) is widened by guard - base margin for the pass, then restored.  OpenSTA credits
  #     the widening back to same-port pairs (CRPR at the common tap port), so only a pair on two tap ports sees it.
  foreach pg_tag {all rr xt} {
    set pg_mrg $pg_pm
    if {$pg_tag eq "rr"} {
      if {$pg_rm <= $pg_pm} { continue }
      if {[llength $pg_in]} { set_false_path -hold -from $pg_in }
      if {[llength $pg_out]} { set_false_path -hold -to $pg_out }
      set pg_mrg $pg_rm
    }
    if {$pg_tag eq "xt"} {
      if {![dict size $pg_taps] || $pg_dg <= 0} {
        puts "OT_PREGRT_FF_HOLD cross-tap guard not applied ([expr {$pg_dg <= 0 ? {guard <= base margin} : {no tap window lines in the kit SDC}}])"
        break
      }
      if {[llength $pg_in]} { set_false_path -hold -from $pg_in }
      if {[llength $pg_out]} { set_false_path -hold -to $pg_out }
      dict for {pg_p pg_v} $pg_taps { lassign $pg_v pg_ck pg_e; set_clock_latency -source -early -clock $pg_ck [expr {$pg_e - $pg_dg}] [get_ports $pg_p] }
    }
    for {set pg_ps 1} {$pg_ps <= 6} {incr pg_ps} {
      set pg_wp [pg_hold]; set pg_np [sta::endpoint_violation_count min]
      if {$pg_wp >= $pg_mrg} break
      repair_timing -hold -hold_margin $pg_mrg -max_buffer_percent 100
      set pg_wq [pg_hold]
      puts "OT_PREGRT_FF_HOLD pass $pg_tag $pg_ps margin $pg_mrg[expr {$pg_tag eq {xt} ? " + cross-tap $pg_dg" : {}}] wns $pg_wq endpoints [sta::endpoint_violation_count min] insts [llength [$pg_blk getInsts]]"
      # lever 3: a pass that still removes >= 5 % of the violating endpoints is progress, whatever the worst endpoint does
      if {$pg_wq >= $pg_mrg || ($pg_wq - $pg_wp < 1.0 && [sta::endpoint_violation_count min] > 0.95 * $pg_np)} break
    }
    if {$pg_tag eq "rr"} {
      if {[llength $pg_in]} { unset_path_exceptions -hold -from $pg_in }; if {[llength $pg_out]} { unset_path_exceptions -hold -to $pg_out }
    }
    if {$pg_tag eq "xt"} {
      set pg_xt [expr {[pg_hold] + $pg_dg}]
      dict for {pg_p pg_v} $pg_taps { lassign $pg_v pg_ck pg_e; set_clock_latency -source -early -clock $pg_ck $pg_e [get_ports $pg_p] }
      if {[llength $pg_in]} { unset_path_exceptions -hold -from $pg_in }
      if {[llength $pg_out]} { unset_path_exceptions -hold -to $pg_out }
    }
    pg_np_apply
  }
  pg_np_end
  # repair_timing seats a hold cell at its driver, on a macro in a macro-dominated tile (V1: 23 cells): legalize all of them
  set pg_nh 0
  foreach pg_i [$pg_blk getInsts] {
    if {[string match "hold*" [$pg_i getName]] || [string match "*/hold*" [$pg_i getName]]} { $pg_i setPlacementStatus PLACED; incr pg_nh }
  }
  # PREGRT-LEGAL-1 (TYPE-KVHROOT 11-14, COORD): a repair that succeeded must not be thrown away by its final legalize.
  # kv3_hroot: 12k hold cells, wns +5.0, then the negotiation legalizer left 79 overlaps in FIRM landing rings, DPL-0033,
  # FALLBACK, and the whole debt went back to the GRT repair (stalled -19.7 / 580).  Order: negotiation legalizer, then
  # the diamond search; if overlaps still remain keep the repaired DB, log the count, later stages re-legalize.
  set pg_legal negotiation; set pg_ovl 0
  if {[catch {detailed_placement; check_placement -verbose} pg_dpe]} {
    puts "OT_PREGRT_FF_HOLD legalize negotiation failed ([lindex [split $pg_dpe "\n"] 0]); retry detailed_placement -use_diamond_legalizer"
    set pg_legal diamond
    if {[catch {detailed_placement -use_diamond_legalizer} pg_dpe2]} { puts "OT_PREGRT_FF_HOLD legalize diamond error ([lindex [split $pg_dpe2 "\n"] 0])" }
    set pg_rep [file join [file dirname [file normalize [info script]]] pregrt_ff_hold_check_placement.rpt]
    if {[catch {check_placement -verbose -report_file_name $pg_rep} pg_dpe3]} {
      set pg_legal diamond+overlaps
      if {[catch {set pg_f [open $pg_rep]; set pg_ovl [regexp -all -line {overlaps|overlap} [read $pg_f]]; close $pg_f}]} { set pg_ovl unknown }
      puts "OT_PREGRT_FF_HOLD legalize RESIDUE overlap_lines $pg_ovl ([lindex [split $pg_dpe3 "\n"] 0]): repaired DB kept, later stages re-legalize"
    }
  }
  puts "OT_PREGRT_FF_HOLD legalize $pg_legal overlaps $pg_ovl"
  estimate_parasitics -placement
} pg_err]} { set pg_fail "tool error: [lindex [split $pg_err "\n"] 0]" }
foreach pg_i $pg_lock { $pg_i setPlacementStatus PLACED }
if {$pg_fail eq ""} {
  set pg_w1 [pg_hold]; set pg_s1 [pg_setup]
  set pg_fail [pg_verdict $pg_w0 $pg_w1 $pg_n0 $pg_s0 $pg_s1 [sta::endpoint_violation_count min] $pg_tn0 [pg_tns]]
}
if {$pg_fail ne ""} {
  puts "OT_PREGRT_FF_HOLD FALLBACK $pg_fail: 4_cts.odb unchanged, the in-flow GRT hold repair takes the whole debt"
} else {
  set pg_open [file join [file dirname [file normalize [info script]]] pregrt_ff_hold_open.tsv]
  if {[catch {pg_classes after $pg_open} pg_err]} { catch {pg_classes after}; puts "OT_PREGRT_FF_HOLD open list not written ($pg_err)" }
  puts "OT_PREGRT_FF_HOLD after wns $pg_w1 endpoints [sta::endpoint_violation_count min] cross_tap_wns $pg_xt tap_ports [dict size $pg_taps] hold_cells $pg_nh insts [llength [$pg_blk getInsts]] setup_wns $pg_s1 (before $pg_s0) guard $pg_guard locked [llength $pg_lock] secs [expr {[clock seconds] - $pg_t0}]"
  write_db $::env(ODB).pg_tmp
  file rename -force $::env(ODB).pg_tmp $::env(ODB)
}
"""


GRT_CONTEXT = r'''# Explicit closed-GRT hold continuation; native TC/BC modes, not the ORFS MM wrapper.
if {![info exists ::env(TLIBS)] || ![llength $::env(TLIBS)]} {error "PREGRT_GRT requires real TC setup and BC hold libraries"}
set pg_grt_dir [file dirname [file normalize [info script]]]
set pg_grt_cf [open [file join $pg_grt_dir config.mk]]
foreach pg_grt_line [split [read $pg_grt_cf] "\n"] {
  if {[regexp {^export\s+(OT_RC_SIGNAL|OT_RC_SIGNAL_SCALE|LAYER_PARASITICS_FILE)\s*=\s*([^#]+)} $pg_grt_line -> k v]} {
    set ::env($k) [string trim $v]
  }
}
close $pg_grt_cf
proc pg_refresh_rc {} {
  estimate_parasitics -global_routing
  if {[info exists ::env(OT_RC_SIGNAL)] && $::env(OT_RC_SIGNAL) eq "1"} {
    source [file join $::pg_grt_dir rc_signal_adjust.tcl]
    ot_rc_signal_table
  }
}
proc pg_grt_ff_taps {} {
  set f [open $::env(SDC)];set txt [read $f];close $f
  set marks [regexp -all -inline -line {^# OT_CORE_TAP_CORNER_FILE[^\n]*$} $txt]
  if {[llength $marks]} {
    if {[llength $marks] != 1 || [string trim [lindex $marks 0]] ne "# OT_CORE_TAP_CORNER_FILE core_taps_ff.sdc"} {error "PREGRT_GRT malformed FF tap marker"}
    read_sdc -mode ff [file join $::pg_grt_dir core_taps_ff.sdc]
  }
}
proc pg_scope_begin {} {
  # Save the actual FF mode, including existing exceptions; restore it before reporting.
  set ::pg_scope_sdc [file join $::pg_grt_dir pregrt_ff_hold_scope.sdc]
  write_sdc -no_timestamp $::pg_scope_sdc
  set ::pg_scope_in [all_inputs -no_clocks];set ::pg_scope_out [all_outputs]
  if {[llength $::pg_scope_in]} {set_false_path -hold -from $::pg_scope_in}
  if {[llength $::pg_scope_out]} {set_false_path -hold -to $::pg_scope_out}
}
proc pg_scope_end {} {
  if {![info exists ::pg_scope_sdc]} return
  if {[llength $::pg_scope_in]} {unset_path_exceptions -hold -from $::pg_scope_in}
  if {[llength $::pg_scope_out]} {unset_path_exceptions -hold -to $::pg_scope_out}
  read_sdc -mode ff $::pg_scope_sdc
  set_mode ff
  unset ::pg_scope_sdc
}
'''


def grt_text(text):
    """Opt-in reuse of the same native TC/BC engine after a closed GRT/TT keep.

    The placement form is returned byte-identical by tcl_text's default path.
    """
    def once(old, new):
        nonlocal text
        if text.count(old) != 1:
            raise ValueError(f"pregrt_ff_hold GRT anchor not unique: {old!r}")
        text = text.replace(old, new, 1)

    text = GRT_CONTEXT + text
    once('  read_sdc -mode ff $::env(SDC)\n',
         '  read_sdc -mode ff $::env(SDC)\n  pg_grt_ff_taps\n')
    if text.count('estimate_parasitics -placement') != 2:
        raise ValueError('pregrt_ff_hold GRT expected exactly two RC refreshes')
    text = text.replace('estimate_parasitics -placement', 'pg_refresh_rc')
    once('set pg_w0 [pg_hold];',
         'puts "OT_PREGRT_GRT_HOLD before full_hold [pg_hold] scope reg2reg rc global_routing"\npg_scope_begin\nset pg_w0 [pg_hold];')
    once('set pg_i0 [llength [$pg_blk getInsts]]; set pg_t0 [clock seconds]',
         'set pg_grt_gate -42.0\nif {[info exists ::env(OT_PREGRT_SETUP_GATE)]} {set pg_grt_gate $::env(OT_PREGRT_SETUP_GATE)}\nif {$pg_s0 < $pg_grt_gate} {error "PREGRT_GRT requires setup-passing TT input: $pg_s0"}\nset pg_i0 [llength [$pg_blk getInsts]]; set pg_t0 [clock seconds]')
    once('if {[catch {\n  # (A)',
         'set pg_grt_active 0\nif {[catch {\n  source [file join $pg_grt_dir grt_pg_replay.tcl]\n  ot_grt_pg_replay_begin $pg_grt_dir\n  global_route -start_incremental\n  set pg_grt_active 1\n  # (A)')
    # Internal scope remains active through both legacy phases and final timing guard.
    once('      if {[llength $pg_in]} { unset_path_exceptions -hold -from $pg_in }\n      if {[llength $pg_out]} { unset_path_exceptions -hold -to $pg_out }',
         '      # The enclosing internal scope is restored only after the timing guard.')
    once('  puts "OT_PREGRT_FF_HOLD legalize $pg_legal overlaps $pg_ovl"\n  pg_refresh_rc',
         '  puts "OT_PREGRT_FF_HOLD legalize $pg_legal overlaps $pg_ovl"\n  if {$pg_legal eq "diamond+overlaps" || $pg_ovl ne "0"} {error "PREGRT_GRT requires legal placement, overlap count $pg_ovl"}\n  set pg_grt_active 0\n  global_route -end_incremental\n  ot_grt_pg_replay_end\n  pg_refresh_rc')
    once('foreach pg_i $pg_lock { $pg_i setPlacementStatus PLACED }',
         'if {$pg_grt_active} {puts "OT_PREGRT_GRT_HOLD abandoned unwritten incremental scene after failure"}\ncatch {ot_grt_pg_replay_end}\nforeach pg_i $pg_lock { $pg_i setPlacementStatus PLACED }')
    once('  set pg_fail [pg_verdict $pg_w0 $pg_w1 $pg_n0 $pg_s0 $pg_s1 [sta::endpoint_violation_count min] $pg_tn0 [pg_tns]]',
         '  set pg_fail [pg_verdict $pg_w0 $pg_w1 $pg_n0 $pg_s0 $pg_s1 [sta::endpoint_violation_count min] $pg_tn0 [pg_tns]]\n  if {$pg_fail eq "" && $pg_s1 < $pg_grt_gate} {set pg_fail "TT setup below gate: $pg_s1"}\n  if {$pg_fail eq "" && $pg_w1 < 0} {set pg_fail "internal FF hold remains negative: $pg_w1"}')
    once('if {$pg_fail ne ""} {\n  puts "OT_PREGRT_FF_HOLD FALLBACK',
         'if {[catch {pg_scope_end} pg_scope_err]} {set pg_fail "scope restore failed: $pg_scope_err"}\nif {$pg_fail ne ""} {\n  puts "OT_PREGRT_FF_HOLD FALLBACK')
    once('  puts "OT_PREGRT_FF_HOLD after wns',
         '  puts "OT_PREGRT_GRT_HOLD restored full_hold [pg_hold] full_endpoints [sta::endpoint_violation_count min] scope reg2reg"\n  puts "OT_PREGRT_FF_HOLD after wns')
    once('  write_db $::env(ODB).pg_tmp',
         '  set pg_guide [file join $pg_grt_dir pregrt_ff_hold.guide]\n  if {[info exists ::env(OT_PREGRT_HOLD_GUIDE)]} {set pg_guide $::env(OT_PREGRT_HOLD_GUIDE)}\n  write_guides $pg_guide\n  write_db $::env(ODB).pg_tmp')
    return text


DIE_CLOCK = {}      # the plan's DIE-level clock block (QC s29 form): a partition type's own clock value wins


def set_die_clock(clock):
    """gen_phys calls this once after the plan validates: DIE-level clock.pregrt_ff_hold / pregrt_hold_guard_ps become the default
    of every type that does not name its own (type-level wins).  Absent = unchanged behaviour."""
    DIE_CLOCK.clear()
    DIE_CLOCK.update({k: v for k, v in (clock or {}).items() if k in ("pregrt_ff_hold", "pregrt_hold_guard_ps")})


def _clock_val(t, key):
    c = t.get("clock") or {}
    return c[key] if key in c else DIE_CLOCK.get(key)


def auto_min():
    """FIX-HOLDSTALL 11-14: die_gen_env OT_PREGRT_FF_HOLD_AUTO = N (1 = default 100) turns the build on for every type whose plan is
    silent, but the kit tcl runs it only when the post-CTS FF hold has >= N register-to-register violators (internal debt).
    None when unset/0.  A plan clock.pregrt_ff_hold false/true always wins."""
    v = os.environ.get("OT_PREGRT_FF_HOLD_AUTO", "").strip()
    if v == "-1":      # KIT-OPS-5 11-14 (COORD class order, TYPE-HDCTLN): always run the build (port/ft hold counts too)
        return -1
    if not v.isdigit() or int(v) <= 0:
        return None
    return 100 if v == "1" else int(v)


def _plan_val(t):
    f = globals().get("_clock_val")
    return f(t, "pregrt_ff_hold") if f else (t.get("clock") or {}).get("pregrt_ff_hold")


def _auto_on(t):
    return _plan_val(t) is None and auto_min() is not None


def enabled(t):
    return _enabled_plan(t) or _auto_on(t)


def _enabled_plan(t):
    """R-CLOCK: opt-in (COORD 11-13 07:2x, default-preserving): on when the type's clock.pregrt_ff_hold is true, or (type silent) the
    plan's die-level clock.pregrt_ff_hold is true."""
    return _clock_val(t, "pregrt_ff_hold") is True


def guard_ps(t):
    """the route guard (ps) the build repairs to: plan clock.pregrt_hold_guard_ps, default GUARD_PS."""
    v = _clock_val(t, "pregrt_hold_guard_ps")
    g = GUARD_PS if v is None else float(v)
    if not 0 <= g <= 100:
        raise ValueError(f"clock.pregrt_hold_guard_ps {g:g} outside [0, 100]")
    return g


def config_lines(t):
    """config.mk lines of the build; [] when the type opts out."""
    if not enabled(t):
        return []
    lines = [CONFIG, f"export OT_PREGRT_HOLD_GUARD = {guard_ps(t):g}"]
    # S81-COL-HOLD-MARGIN 11-17 (COORD): per-item knob OT_PREGRT_HOLD_PORT_MARGIN_PS (kit_wave item_env) sets the pre-GRT same-tap /
    # port hold margin (tcl default 5 ps) of THIS kit only; unset or empty = today's behaviour (no line, the tcl default applies).
    pm = os.environ.get("OT_PREGRT_HOLD_PORT_MARGIN_PS", "").strip()
    if pm:
        lines.append(f"export OT_PREGRT_HOLD_PORT_MARGIN = {float(pm):g}")
    return lines


def tcl_text(hold_gate_text, amin=-1, *, rc_basis="placement"):
    if hold_gate_text.count(MARK) != 1:
        raise ValueError("pregrt_ff_hold: hold_gate.tcl context marker not found exactly once; fails closed")
    head = hold_gate_text.split(MARK)[0]
    if head.count(READ) != 1:
        raise ValueError("pregrt_ff_hold: hold_gate.tcl library / database read not found exactly once; fails closed")
    text = head.replace(READ, READ2) + TAIL.replace("@PG_AUTO_MIN@", str(int(amin)))
    if rc_basis not in ("placement", "global_routing"):
        raise ValueError(f"unsupported hold RC basis {rc_basis!r}")
    return grt_text(text) if rc_basis == "global_routing" else text


def install(t, kd, *, rc_basis="placement"):
    """Kit tcl (run_kit.sh runs it when config.mk says OT_PREGRT_FF_HOLD = 1).  False (no writes) when opted out."""
    if not enabled(t):
        return False
    kd = Path(kd)
    (kd / "pregrt_ff_hold.tcl").write_text(tcl_text((kd / "hold_gate.tcl").read_text(), auto_min() if _auto_on(t) else -1, rc_basis=rc_basis))
    return True


if __name__ == "__main__":      # pregrt_ff_hold.py KIT [GUARD]: stage the build into an existing kit (private proofs)
    import sys
    kit = Path(sys.argv[1])
    g = float(sys.argv[2]) if len(sys.argv) > 2 else GUARD_PS
    install({"clock": {"pregrt_ff_hold": True}}, kit)
    c = (kit / "config.mk").read_text()
    if CONFIG not in c:
        (kit / "config.mk").write_text(c.rstrip("\n") + f"\n{CONFIG}\nexport OT_PREGRT_HOLD_GUARD = {g:g}\n")
    print("staged", kit / "pregrt_ff_hold.tcl")
