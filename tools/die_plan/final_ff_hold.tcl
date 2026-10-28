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
