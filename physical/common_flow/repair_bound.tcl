# FLOW-FIX-2045 (COORD, LONG-RUN-0300: QC cbn_q00__cld7bf7197 sat in the post-GRT repair_timing for 150+ iterations at WNS -242.069 with 0 fixes): ORFS step hook (PRE_GLOBAL_ROUTE, sourced last).
# The in-flow repair_timing_helper (post-GRT setup / hold repair) runs in chunks of OT_REPAIR_CHUNK iterations (default 50 here: one iteration of a big GRT-stage repair takes minutes) and stops when
# neither worst setup nor worst hold slack improved by 1 ps over OT_REPAIR_STALL_CHUNKS chunks (3), when OT_REPAIR_MAX_S (7200 s, 0 = off) is used, or at OT_MAX_ITERATIONS (4000); then the stage goes on
# with the design as repaired so far.  Lines: OT_REPAIR_STALL / OT_REPAIR_WALLCAP post_grt_repair ...  Constraints, margins and corners are unchanged.  OT_REPAIR_BOUND=0 = off.
# FLOW-FIX-2045 (COORD lever 8, FABLE-CLOSURE: S81 lepe proof5 ran 9 h / 3,200 repair iterations flat at -270 and left no DB): the repair is run in chunks of OT_REPAIR_CHUNK iterations
# (default 200) and ends when neither measured slack improved by 1 ps over OT_REPAIR_STALL_CHUNKS chunks (default 3), when the wall time OT_REPAIR_MAX_S (default 7200 s, 0 = off) is used,
# or when the old total cap is reached.  The caller then writes its DB and reports as if the repair had converged; "OT_REPAIR_STALL" / "OT_REPAIR_WALLCAP" lines name why it stopped.
proc ::ot_bounded_repair {label run_chunk measure total} {
  set chunk 200; set stall_n 3; set max_s 7200
  if {[info exists ::env(OT_REPAIR_CHUNK)] && [string is integer -strict $::env(OT_REPAIR_CHUNK)] && $::env(OT_REPAIR_CHUNK) > 0} { set chunk $::env(OT_REPAIR_CHUNK) }
  if {[info exists ::env(OT_REPAIR_STALL_CHUNKS)] && [string is integer -strict $::env(OT_REPAIR_STALL_CHUNKS)] && $::env(OT_REPAIR_STALL_CHUNKS) > 0} { set stall_n $::env(OT_REPAIR_STALL_CHUNKS) }
  if {[info exists ::env(OT_REPAIR_MAX_S)] && [string is integer -strict $::env(OT_REPAIR_MAX_S)]} { set max_s $::env(OT_REPAIR_MAX_S) }
  set t0 [clock seconds]; set done 0; set stall 0
  lassign [{*}$measure] best_s best_h
  while {$done < $total} {
    set n [expr {min($chunk, $total - $done)}]
    {*}$run_chunk $n
    incr done $n
    lassign [{*}$measure] s h
    set better 0
    if {$s ne "" && $best_s ne "" && $s > $best_s + 1.0} { set better 1 }
    if {$h ne "" && $best_h ne "" && $h > $best_h + 1.0} { set better 1 }
    if {$s ne "" && ($best_s eq "" || $s > $best_s)} { set best_s $s }
    if {$h ne "" && ($best_h eq "" || $h > $best_h)} { set best_h $h }
    if {$better} { set stall 0 } else { incr stall }
    if {($s eq "" || $s >= 0) && ($h eq "" || $h >= 0)} { break }
    if {$stall >= $stall_n} {
      puts "OT_REPAIR_STALL $label stop after $done iterations: slack improved < 1 ps in the last $stall chunks of $chunk (setup $s hold $h)"
      break
    }
    if {$max_s > 0 && [clock seconds] - $t0 >= $max_s} {
      puts "OT_REPAIR_WALLCAP $label stop after $done iterations, [expr {[clock seconds] - $t0}] s (cap $max_s s; setup $s hold $h)"
      break
    }
  }
  return $done
}
if {[info procs repair_timing_helper] ne "" && [info procs ot_rb_orig_rth] eq "" && (![info exists ::env(OT_REPAIR_BOUND)] || $::env(OT_REPAIR_BOUND) ne "0")} {
  if {![info exists ::env(OT_REPAIR_CHUNK)]} { set ::env(OT_REPAIR_CHUNK) 50 }
  rename repair_timing_helper ot_rb_orig_rth
  proc ::ot_rb_measure {} {
    if {[catch {list [sta::worst_slack -max] [sta::worst_slack -min]} r]} { return [list "" ""] }
    return $r
  }
  proc ::ot_rb_chunk {helper_args n} { ot_rb_orig_rth {*}$helper_args -max_iterations $n }
  proc repair_timing_helper {args} {
    set total 4000
    if {[info exists ::env(OT_MAX_ITERATIONS)] && [string is integer -strict $::env(OT_MAX_ITERATIONS)] && $::env(OT_MAX_ITERATIONS) > 0} { set total $::env(OT_MAX_ITERATIONS) }
    ot_bounded_repair post_grt_repair [list ::ot_rb_chunk $args] ::ot_rb_measure $total
  }
}
