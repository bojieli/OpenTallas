# HOLD-GUARD-GRT (FLOW-23 2026-11-02): progress/time bound for the single-mode GRT hold repair.
# CLASS [CHECKED 11-02 22:3x, docker scan of running kits on epyc2/intel1/intel2]: gen_phys type kits (dpkit-*) and the
# other single-mode kit runners call ORFS repair_timing_helper with NO hold progress limit (the hold-stall guard in
# tools/orfs_hold_mm.tcl, ot_repair_timing, is installed only in two-mode OT_HOLD_MM kits).  S81 slice_station kits sat
# 27-47 h in 5_1_grt hold repair with WNS frozen (t40/t24 since 11-01 07:39 UTC, t18/t8/t22 since 11-02); the s81_cl
# flow canary 26360778f hung 44 h at iteration 11050 (WNS -55.1 flat, TNS -183 -> -36 ns, 21k buffers, ~4 it/min).
# Rule (same intent as the two-mode guard, no margin/corner/constraint/acceptance change): a GRT repair_timing call that
# includes hold runs setup exactly as before, then hold in buffer-capped chunks (-max_buffer_percent, ~OT_HOLD_CHUNK_S
# = 900 s each, adaptive); it stops when hold reaches the requested margin, when hold is >= 0 and a chunk gains < 1 ps,
# when one OT_HOLD_STALL_WINDOW_S (3600 s) of repair gains < 1 ps WNS and < OT_HOLD_MIN_GAIN_PCT (2) % TNS, after
# OT_HOLD_MAX_HOURS (3) h, when a chunk adds no buffer, or when a chunk ends below its cap (the native repair finished:
# the guard never runs longer than the unchunked call would).  The residue goes to route / sign-off / post-route hold ECO
# (owner: late-stage iteration).  The call's own total budget (-max_buffer_percent, else 20 %) is kept.
# Inert when OT_HOLD_GUARD=0, when the orfs_hold_mm two-mode guard (ot_repair_timing) is present, or for setup-only calls.
if {[llength [info procs ::repair_timing_helper]] && ![llength [info procs ::ot_hg_rth_orig]] &&
    ![llength [info commands ot_repair_timing]] &&
    (![info exists ::env(OT_HOLD_MM)] || $::env(OT_HOLD_MM) ne "1") &&
    (![info exists ::env(OT_HOLD_GUARD)] || $::env(OT_HOLD_GUARD) ne "0")} {
  rename ::repair_timing_helper ::ot_hg_rth_orig
  proc ::ot_hg_num {k d} { expr {[info exists ::env($k)] && [string is double -strict $::env($k)] ? $::env($k) : $d} }
  proc ::ot_hg_stats {} {
    set w [worst_slack -min]
    set t [total_negative_slack -min]
    set n -1; catch { set n [sta::endpoint_violation_count min] }
    return [list $w $t $n]
  }
  proc ::ot_hg_strip {args_in flag {val 0}} {
    set out {}
    for {set i 0} {$i < [llength $args_in]} {incr i} {
      if {[lindex $args_in $i] eq $flag} { if {$val} { incr i }; continue }
      lappend out [lindex $args_in $i]
    }
    return $out
  }
  proc ::repair_timing_helper {args} {
    set has_s [expr {[lsearch -exact $args -setup] >= 0}]
    set has_h [expr {[lsearch -exact $args -hold] >= 0}]
    if {$has_s && !$has_h} { return [::ot_hg_rth_orig {*}$args] }
    set tot 20.0
    set j [lsearch -exact $args -max_buffer_percent]; if {$j >= 0} { set tot [lindex $args [expr {$j + 1}]] }
    set base [::ot_hg_strip [::ot_hg_strip [::ot_hg_strip $args -setup] -hold] -max_buffer_percent 1]
    if {!$has_h || $has_s} { ::ot_hg_rth_orig {*}$base -setup -max_buffer_percent $tot }
    set hm [::ot_hg_num HOLD_SLACK_MARGIN 0.0]
    set j [lsearch -exact $args -hold_margin]; if {$j >= 0} { set hm [lindex $args [expr {$j + 1}]] }
    if {[catch {set prev [::ot_hg_stats]} msg]} {
      puts "OT_HOLD_GUARD_GRT: hold stats unavailable ($msg); unguarded hold repair"
      return [::ot_hg_rth_orig {*}$base -hold -max_buffer_percent $tot]
    }
    set block [ord::get_db_block]
    set inst0 [llength [$block getInsts]]
    set cs [::ot_hg_num OT_HOLD_CHUNK_S 900]
    set bmin [::ot_hg_num OT_HOLD_CHUNK_BUF_MIN 200]
    set bmax [expr {max(2000.0, [::ot_hg_num OT_HOLD_CHUNK_BUF_PCT 1.0] * $inst0 / 100.0)}]
    set win [::ot_hg_num OT_HOLD_STALL_WINDOW_S 3600]
    set mingain [::ot_hg_num OT_HOLD_MIN_GAIN_PCT 2.0]
    set maxs [expr {[::ot_hg_num OT_HOLD_MAX_HOURS 3.0] * 3600}]
    set nb [expr {max($bmin, 0.0025 * $inst0)}]
    set t0 [clock seconds]; set wt $t0; set wstat $prev; set capped 0
    puts [format "OT_HOLD_GUARD_GRT start: hold ws %.2f tns %.1f viol %d, margin %g, %d instances, budget %g %%" \
      {*}$prev $hm $inst0 $tot]
    for {set k 1} {1} {incr k} {
      if {[lindex $prev 0] >= $hm} { break }
      set inst [llength [$block getInsts]]
      set left [expr {$tot * $inst0 / 100.0 - ($inst - $inst0)}]
      if {$left < 1} { puts "OT_HOLD_GUARD_GRT: total buffer budget $tot % used, stop"; break }
      set nb [expr {min($nb, $left)}]
      set pct [format %.6f [expr {100.0 * max($nb, 1.0) / $inst}]]
      set tc [clock seconds]
      set hit 0
      # FLOW-24 11-03: the chunk cap is the guard's own stop, not a tool failure.  RSZ-0060 is suppressed for the chunk
      # call so no [ERROR RSZ-0060] line lands in 5_1_grt.log (kit_resume ERR_LINE judged the completed GRT stage failed;
      # the flow canary counted it as a Tcl error).  A suppressed error may reach Tcl without its text, so a chunk that
      # raised and added >= 95 % of its cap is the cap; any other error is re-raised unchanged.
      catch {suppress_message RSZ 60}
      set rc [catch {::ot_hg_rth_orig {*}$base -hold -max_buffer_percent $pct} err opts]
      catch {unsuppress_message RSZ 60}
      set added [expr {[llength [$block getInsts]] - $inst}]
      if {$rc} {
        if {![regexp {RSZ-0060|Max buffer count} $err] && $added < 0.95 * $nb} { return -options $opts $err }
        set capped 1; set hit 1
      }
      set cur [::ot_hg_stats]
      set dt [expr {max(1, [clock seconds] - $tc)}]
      set dw [expr {[lindex $cur 0] - [lindex $prev 0]}]
      lassign $cur cw ct cv
      puts [format "OT_HOLD_GUARD_GRT chunk %d: hold ws %.2f (%+.2f) tns %.1f viol %d, +%d buffers (cap %.0f), %d s" \
        $k $cw $dw $ct $cv $added $nb $dt]
      set prev $cur
      if {[lindex $cur 0] >= $hm} { break }
      if {[lindex $cur 0] >= 0 && $dw < 1.0} { puts "OT_HOLD_GUARD_GRT: hold met (ws >= 0), margin chase stalled, stop"; break }
      if {$added <= 0} { puts "OT_HOLD_GUARD_GRT: chunk added no buffer, stop"; break }
      # the chunk ended below its buffer cap = the native repair finished on its own: same end as an unchunked call
      if {!$hit} { puts "OT_HOLD_GUARD_GRT: native hold repair finished inside the chunk, stop"; break }
      set now [clock seconds]
      if {$now - $wt >= $win} {
        lassign $wstat w0 tn0; lassign $cur w1 tn1
        set gain [expr {$tn0 < 0 ? 100.0 * ($tn1 - $tn0) / abs($tn0) : 0.0}]
        if {$w1 - $w0 < 1.0 && $gain < $mingain} {
          puts [format "OT_HOLD_STALL NEEDS_RTL stage=grt reason=stalled: %d s gained %.2f ps WNS / %.1f %% TNS (ws %.2f tns %.1f viol %d)" \
            [expr {$now - $wt}] [expr {$w1 - $w0}] $gain {*}$cur]
          break
        }
        set wt $now; set wstat $cur
      }
      if {$now - $t0 >= $maxs} {
        puts [format "OT_HOLD_STALL NEEDS_RTL stage=grt reason=hold repair over %g h (ws %.2f tns %.1f viol %d)" [expr {$maxs / 3600.0}] {*}$cur]
        break
      }
      set nb [expr {min($bmax, max($bmin, double($added) / $dt * $cs))}]
    }
    if {$capped} { puts "OT_HOLD_GUARD_GRT: chunk buffer caps reached (RSZ-0060 suppressed per chunk); continuing on the repaired design" }
  }
  puts "OT_HOLD_GUARD_GRT installed (single-mode GRT hold repair progress/time bound)"
}
