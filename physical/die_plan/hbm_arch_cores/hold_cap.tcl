# ELEM-HBM 10-24 (PRE_GLOBAL_ROUTE hook): the CP1-R10 kit IO standard (input min delay -insertion_tol vs the IO virtual
# clock at the plan insertion) asks every pin-registered input for ~45-90 ps of hold delay; on 4-6k-input cores that
# exceeds ORFS repair_timing's default 20 % buffer cap (RSZ-0060).  Raise the tool cap only (OT_MAX_BUFFER_PERCENT,
# default 100); constraints, margins and corners are unchanged.
# HBM-ELEM 10-24: + an iteration cap (OT_MAX_ITERATIONS, default 4000).  54 idx_score_quarter routes looped for hours
# in the GRT hold repair on ONE endpoint (WNS / TNS flat for >3000 iterations, 2 buffers added per 10 iterations): the
# cap ends the loop so the run reaches route + signoff, which reports the residual honestly (FF hold STA decides).
# source_step_tcl sources this inside a proc: keep the value in a namespace variable.
set ::ot_mbp [expr {[info exists ::env(OT_MAX_BUFFER_PERCENT)] ? $::env(OT_MAX_BUFFER_PERCENT) : 100}]
set ::ot_mit [expr {[info exists ::env(OT_MAX_ITERATIONS)] ? $::env(OT_MAX_ITERATIONS) : 4000}]
rename ::repair_timing_helper ::ot_repair_timing_helper_orig
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
proc ::ot_hc_measure {} {
  if {[catch {list [sta::worst_slack -max] [sta::worst_slack -min]} r]} { return [list "" ""] }
  return $r
}
proc ::ot_hc_chunk {helper_args n} {
  ::ot_repair_timing_helper_orig {*}$helper_args -max_buffer_percent $::ot_mbp -max_iterations $n
}
proc ::repair_timing_helper { args } {
  puts "OT_HOLD_CAP repair_timing -max_buffer_percent $::ot_mbp -max_iterations $::ot_mit (chunked, stall / wall-time bound)"
  ::ot_bounded_repair repair_timing_helper [list ::ot_hc_chunk $args] ::ot_hc_measure $::ot_mit
}
