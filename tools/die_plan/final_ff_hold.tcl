# Optional post-GRT residual FF hold repair in the kit's existing TT/FF frames.
# Measured failure: coll_q2 reduce e2ba1ba7dd28 repairs hold before DPL/reroute,
# then reaches the final FF gate at -0.34 ps (TT setup +27.43 ps).
# Called only by a reviewed --final-ff-hold HBM kit; no default hook changes.
set ::ot_final_ff_tooldir [file dirname [file normalize [info script]]]

proc ot_final_ff_rc {} {
  if {![info exists ::env(LAYER_PARASITICS_FILE)] || ![file isfile $::env(LAYER_PARASITICS_FILE)]} {
    error "OT_FINAL_FF_HOLD: selected kit RC model unavailable"
  }
  source $::env(LAYER_PARASITICS_FILE)
  estimate_parasitics -global_routing
}

proc ot_final_ff_hold {} {
  if {![info exists ::env(OT_HOLD_MM)] || $::env(OT_HOLD_MM) ne "1" ||
      ![info exists ::ot_mm_active] || !$::ot_mm_active ||
      ![llength [info commands ot_mm_sync]] || ![llength [info commands ot_mm_ws]] ||
      [string toupper [ot_mm_sc]] ni {TC TT} || $::ot_mm_stage ne "4_cts.sdc"} {
    error "OT_FINAL_FF_HOLD: actual patched TT/BC GRT session required"
  }
  set hm 0
  foreach k {OT_HOLD_FF_MARGIN HOLD_SLACK_MARGIN} {
    if {[info exists ::env($k)] && [string is double -strict $::env($k)]} {
      set hm $::env($k); break
    }
  }
  set d [file join $::env(RESULTS_DIR) final_ff_[clock microseconds]]
  file mkdir $d
  ot_mm_unsync
  ot_mm_sync
  try {
    ot_final_ff_rc
    set tt0 [ot_mm_ws max [ot_mm_sc]]
    set ff0 [ot_mm_ws min BC]
    puts "OT_FINAL_FF_HOLD before TT_setup $tt0 FF_hold $ff0 hold_margin $hm"
    if {$tt0 < 0} { error "OT_FINAL_FF_HOLD: TT setup already negative ($tt0), revise before residual hold repair" }
    if {$ff0 >= 0} {
      puts "OT_FINAL_FF_HOLD PASS no repair needed"
      return
    }
    if {[info exists ::env(OT_CLK_FREEZE)] && $::env(OT_CLK_FREEZE) ne "1"} {
      error "OT_FINAL_FF_HOLD: clock freeze cannot be disabled"
    }
    source [file join $::ot_final_ff_tooldir clk_freeze.tcl]
    ot_clk_freeze $d
    global_route -start_incremental
    # Both scenes are active: hold buffers must retain the real TT setup guard.
    # No clock sizing/latency change and no new repair margin is introduced.
    repair_timing -hold -hold_margin $hm -max_buffer_percent 100
    detailed_placement
    check_placement -verbose
    global_route -end_incremental
    ot_clk_freeze_assert final_ff
    ot_final_ff_rc
    # Rebuild the FF mode from the unchanged kit SDC after legalization/routing.
    ot_mm_unsync
    ot_mm_sync
    ot_final_ff_rc
    set tt1 [ot_mm_ws max [ot_mm_sc]]
    set ff1 [ot_mm_ws min BC]
    ot_clk_dump $d/clk_freeze_post.tsv post $d/clk_freeze_nets.txt
    set check [file join $::ot_final_ff_tooldir clk_geom_diff.py]
    if {[catch {exec python3 -I $check $d/clk_freeze_pre.tsv $d/clk_freeze_post.tsv --json $d/clock_diff.json} msg]} {
      error "OT_FINAL_FF_HOLD: clock geometry changed: $msg"
    }
    puts $msg
    puts "OT_FINAL_FF_HOLD after TT_setup $tt1 FF_hold $ff1"
    if {$tt1 < 0 || $ff1 < 0} {
      error "OT_FINAL_FF_HOLD FAIL after legalization/routing: TT setup $tt1 FF hold $ff1"
    }
    puts "OT_FINAL_FF_HOLD PASS repaired and rechecked"
  } on error {msg opts} {
    # Keep the completed corrective state if the final checks fail.
    catch {write_db $d/final_failed.odb}
    return -options $opts $msg
  } finally {
    ot_mm_unsync
  }
}

# Opt-in fixed-point repair for kits whose final legalization/routing changes
# the actual hold/DRV result. The ordinary ot_final_ff_hold entry is unchanged.
# Invoke from the reviewed kit's POST_GLOBAL_ROUTE hook, before PG binding.
# Progress is a changed physical/netlist state, never an arbitrary pass budget.
proc ot_final_ff_state {} {
  set rows {}
  foreach i [[ord::get_db_block] getInsts] {
    set pins {}
    foreach it [$i getITerms] {
      set net [$it getNet]
      lappend pins [list [[$it getMTerm] getName] [expr {$net eq "NULL" ? "" : [$net getName]}]]
    }
    lappend rows [list [$i getName] [[$i getMaster] getName] [$i getOrigin] [$i getOrient] [lsort $pins]]
  }
  return [lsort $rows]
}
proc ot_final_ff_refresh {} {
  # The FF arrival shim measures clocks while syncing: selected RC MUST already
  # be active. Temporary hold RC must not leak into the final measured frame.
  ot_mm_unsync
  ot_final_ff_rc
  ot_mm_sync
  ot_final_ff_rc
}
proc ot_final_ff_counts {} {
  list [sta::max_slew_violation_count] [sta::max_capacitance_violation_count]
}
proc ot_final_ff_converge {} {
  if {![info exists ::env(OT_HOLD_MM)] || $::env(OT_HOLD_MM) ne "1" ||
      ![info exists ::ot_mm_active] || !$::ot_mm_active ||
      [string toupper [ot_mm_sc]] ni {TC TT} || $::ot_mm_stage ne "4_cts.sdc"} {
    error "OT_FINAL_FF_CONVERGE: actual patched TT/BC GRT session required"
  }
  if {[info exists ::env(OT_CLK_FREEZE)] && $::env(OT_CLK_FREEZE) ne "1"} {
    error "OT_FINAL_FF_CONVERGE: clock freeze cannot be disabled"
  }
  set hm 0
  foreach k {OT_HOLD_FF_MARGIN HOLD_SLACK_MARGIN} {
    if {[info exists ::env($k)] && [string is double -strict $::env($k)]} {
      set hm $::env($k); break
    }
  }
  set d [file join $::env(RESULTS_DIR) final_converge_[clock microseconds]]
  file mkdir $d
  set seen [dict create]
  set pass 0
  try {
    ot_final_ff_refresh
    source [file join $::ot_final_ff_tooldir clk_freeze.tcl]
    ot_clk_freeze $d
    while {1} {
      set tt [ot_mm_ws max [ot_mm_sc]]
      set ff [ot_mm_ws min BC]
      lassign [ot_final_ff_counts] slew cap
      if {![string is double -strict $tt] || ![string is double -strict $ff] ||
          ![string is integer -strict $slew] || ![string is integer -strict $cap] || $slew < 0 || $cap < 0} {
        error "OT_FINAL_FF_CONVERGE: missing actual timing/DRV metrics"
      }
      puts "OT_FINAL_FF_CONVERGE pass $pass TT_setup $tt FF_hold $ff slew $slew cap $cap hold_margin $hm"
      if {$tt < 0} { error "OT_FINAL_FF_CONVERGE: TT setup negative ($tt); structural revision required" }
      ot_clk_freeze_assert final_converge
      ot_clk_dump $d/clk_freeze_post.tsv post $d/clk_freeze_nets.txt
      set check [file join $::ot_final_ff_tooldir clk_geom_diff.py]
      if {[catch {exec python3 -I $check $d/clk_freeze_pre.tsv $d/clk_freeze_post.tsv --json $d/clock_diff.json} msg]} {
        error "OT_FINAL_FF_CONVERGE: clock geometry changed: $msg"
      }
      if {$ff >= 0 && $slew == 0 && $cap == 0} {
        puts "OT_FINAL_FF_CONVERGE PASS actual selected-RC TT/FF/DRV after routing"
        break
      }
      set state [list [ot_final_ff_state] $tt $ff $slew $cap]
      if {[dict exists $seen $state]} {
        error "OT_FINAL_FF_CONVERGE: repeated physical state with unresolved hold/DRV; structural revision required"
      }
      dict set seen $state 1
      global_route -start_incremental
      if {$slew || $cap} {
        # Reuse the kit's own maximum-wire and slew/cap margins unchanged.
        if {![llength [info commands repair_design_helper]]} {
          error "OT_FINAL_FF_CONVERGE: kit repair_design_helper unavailable"
        }
        repair_design_helper
        # Legalize and route these changed loads before the next hold check.
      } elseif {$ff < 0} {
        repair_timing -hold -hold_margin $hm -max_buffer_percent 100
      }
      detailed_placement
      check_placement -verbose
      global_route -end_incremental
      ot_final_ff_refresh
      set next_ff [ot_mm_ws min BC]
      lassign [ot_final_ff_counts] next_slew next_cap
      if {$slew || $cap} {
        if {$next_slew + $next_cap >= $slew + $cap} {
          error "OT_FINAL_FF_CONVERGE: no actual DRV-count improvement after routing; structural revision required"
        }
      } elseif {$next_ff <= $ff || $next_slew || $next_cap} {
        error "OT_FINAL_FF_CONVERGE: no actual FF improvement or new DRV after hold routing; structural revision required"
      }
      incr pass
    }
  } on error {msg opts} {
    catch {write_db $d/final_failed.odb}
    return -options $opts $msg
  } finally {
    ot_mm_unsync
  }
}
