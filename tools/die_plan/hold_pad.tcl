# HOLD-PAD-FLOW 11-24 (OWNER/COORD: "hold repair keeps stalling").  PLANNED HOLD PAD: the FF hold debt of every endpoint is a
# measured number, so the pad is computed, not searched.  repair_timing -hold searches one buffer at a time per endpoint and
# re-times between moves; on a kit with tens of thousands of reg-to-reg violators at the family margin it stalls:
#   QC 11-24: 8 kits (slw_hc2/hc3, slw_st_b_v1/v2, sle_st_b_v2) sat 2.5 h at "iteration 0" of the 40 ps rr pass
#     (slw_hc3: 61,420 endpoints, no progress row in 2 h, NOPROG-TABLE 08:45);
#   HEAD hd_tile re-sign 11-24: repair_timing -hold added 1 buffer per pass with no gain (u_eB/fault -> flt_q[4]); the
#     planned pad (HEAD-TILE-RESIGN, 542 HB4xp67 at 329 capture registers, n = ceil((margin - slack) / 37 ps)) closed it in
#     one pass: FF hold -72.31 -> +1.11, TT setup +12.06 unchanged.
# Method, per endpoint (one pass; the caller may call it again on the residual):
#   1. every hold path end below `margin` in the CURRENT hold context (the caller's exceptions apply), worst first;
#      only standard-cell sequential data pins (no port, no macro pin, no async set/reset pin, no clock net);
#   2. n = ceil((margin - slack) / OT_HOLD_PAD_FF_PS) pad cells (default HB4xp67, 37 ps FF each), at most OT_HOLD_PAD_MAX_PER_END (4);
#   3. TT SETUP HEADROOM: the same endpoint's worst setup slack s_tt (the TT scene of a two-scene session; else the only scene)
#      must keep s_tt - n * OT_HOLD_PAD_TT_PS (60 ps, HB4xp67 TT at small load) >= OT_HOLD_PAD_SETUP_FLOOR (0 ps): n is cut to
#      the headroom, an endpoint with none is left to the in-flow repair (counted setup_blocked);
#   4. insert the n cells in front of that one load pin (insert_buffer -load_pins: no other sink of the net moves), at the
#      register's site; the caller legalizes (detailed_placement).
# At most `budget` cells per call (0 = OT_HOLD_PAD_MAX_CELLS, default max(2000, 5 % of the instances)), worst endpoints first.
# Writes <dir>/hold_pad_<tag>.tsv (endpoint, hold slack, TT setup slack, cells) and one summary line; returns the cell count.
# Standalone use (route-keeping ECOs): source hold_pad.tcl; ot_hold_pad eco 20 ; then legalize + incremental route.
proc ot_hp_env {k d} { expr {[info exists ::env($k)] && [string is double -strict $::env($k)] ? $::env($k) : $d} }
proc ot_hold_pad {tag margin {budget 0} {dir ""}} {
  set cell [expr {[info exists ::env(OT_HOLD_PAD_CELL)] && $::env(OT_HOLD_PAD_CELL) ne "" ? $::env(OT_HOLD_PAD_CELL) : "HB4xp67_ASAP7_75t_R"}]
  set ff_ps [ot_hp_env OT_HOLD_PAD_FF_PS 37.0]
  set tt_ps [ot_hp_env OT_HOLD_PAD_TT_PS 60.0]
  set floor [ot_hp_env OT_HOLD_PAD_SETUP_FLOOR 0.0]
  set maxn [expr {int([ot_hp_env OT_HOLD_PAD_MAX_PER_END 4])}]
  set blk [ord::get_db_block]
  if {$budget <= 0} {
    set budget [expr {int([ot_hp_env OT_HOLD_PAD_MAX_CELLS [expr {max(2000, int(ceil(0.05 * [llength [$blk getInsts]])))}]])}]
  }
  if {$dir eq ""} { set dir [expr {[info exists ::env(RESULTS_DIR)] && [file isdirectory $::env(RESULTS_DIR)] ? $::env(RESULTS_DIR) : [file dirname [file normalize [info script]]]}] }
  set lc [get_lib_cells -quiet */$cell]
  if {![llength $lc]} { error "OT_HOLD_PAD no library cell $cell" }
  unset_dont_use $lc
  set t0 [clock seconds]
  set async [dict create]
  foreach p [all_registers -async_pins] { dict set async [get_full_name $p] 1 }
  # 1. hold ends below the margin, worst first
  set ends {}; set skip 0
  foreach pe [find_timing_paths -path_delay min -group_path_count 3000000 -endpoint_path_count 1 -slack_max [expr {$margin - 1e-3}]] {
    set s [get_property $pe slack]
    set pin [get_property $pe endpoint]
    if {[dict exists $async [get_full_name $pin]]} { incr skip; continue }
    set it [sta::sta_to_db_pin $pin]
    if {$it eq "NULL" || $it eq ""} { incr skip; continue }
    set inst [$it getInst]; set m [$inst getMaster]
    if {[$m isBlock] || ![$m isSequential] || [$it getNet] eq "NULL" || [[$it getNet] getSigType] eq "CLOCK"} { incr skip; continue }
    set mt [$it getMTerm]
    if {[$mt getSigType] in {RESET SCAN CLOCK} || [regexp {^(SETN|RESETN|SN|RN|SET|RESET|CLR|PRE)$} [$mt getName]]} { incr skip; continue }
    lappend ends [list $s $pin $it [get_full_name $pin]]
  }
  set ends [lsort -real -index 0 $ends]
  # 3. TT setup slack of the same endpoints (one query; unconstrained setup = unlimited headroom)
  set tts [dict create]
  if {[llength $ends]} {
    if {[catch {
      set pins {}; foreach e $ends { lappend pins [lindex $e 1] }
      for {set i 0} {$i < [llength $pins]} {incr i 20000} {
        foreach pe [find_timing_paths -path_delay max -to [lrange $pins $i [expr {$i + 19999}]] -group_path_count 3000000 -endpoint_path_count 1] {
          dict set tts [get_full_name [get_property $pe endpoint]] [get_property $pe slack]
        }
      }
    } err]} {
      # no per-endpoint setup: every endpoint gets the design's worst setup slack as its headroom (conservative)
      set w [sta::time_sta_ui [sta::worst_slack_cmd max]]
      puts "OT_HOLD_PAD $tag per-endpoint setup unavailable ([lindex [split $err \n] 0]): headroom = design setup wns $w"
      foreach e $ends { dict set tts [lindex $e 3] $w }
    }
  }
  # 2 + 4. plan and insert
  set tot 0; set k 0; set blocked 0; set cut 0; set clamped 0; set over 0
  set fp [open [file join $dir hold_pad_${tag}.tsv] w]
  puts $fp "endpoint\thold_slack_ps\ttt_setup_slack_ps\tcells\tnote"
  foreach e $ends {
    lassign $e s pin it en
    set n [expr {int(ceil(($margin - $s) / $ff_ps))}]
    set note ""
    if {$n > $maxn} { set n $maxn; incr clamped; set note "clamped $maxn" }
    set st [expr {[dict exists $tts $en] ? [dict get $tts $en] : "inf"}]
    if {![string is double -strict $st] || $st > 1e6} { set st inf }
    if {$st ne "inf"} {
      set nh [expr {int(floor(($st - $floor) / $tt_ps))}]
      if {$nh < $n} { set n [expr {max(0, $nh)}]; if {$n == 0} { incr blocked; set note "setup_blocked" } else { incr cut; set note "setup_cut" } }
    }
    if {$n > 0 && $tot + $n > $budget} { incr over; set n 0; set note "budget" }
    puts $fp "$en\t[format %.2f $s]\t$st\t$n\t$note"
    if {$n <= 0} continue
    set loc [[$it getInst] getLocation]
    set xy [list [ord::dbu_to_microns [lindex $loc 0]] [ord::dbu_to_microns [lindex $loc 1]]]
    for {set j 0} {$j < $n} {incr j} {
      insert_buffer -buffer_cell $cell -load_pins [list $pin] -location $xy -buffer_name hold_pad_${tag}_${k}_$j
      incr tot
    }
    incr k
  }
  close $fp
  puts [format "OT_HOLD_PAD %s margin %.1f ends %d padded %d cells %d (%s %.0f ps FF / %.0f ps TT, floor %.1f) setup_blocked %d setup_cut %d clamped %d over_budget %d (budget %d) skipped_nonreg %d secs %d" \
    $tag $margin [llength $ends] $k $tot $cell $ff_ps $tt_ps $floor $blocked $cut $clamped $over $budget $skip [expr {[clock seconds] - $t0}]]
  return $tot
}
