# Pure discrete projection for a stalled MSCTS tap-window balancer.
# No source-time activation, database edits, target/constraint changes or RC claims.
# Caller supplies actual measured per-tap pad delays (ps) and verifies the chosen
# edits with incremental GRT RC.  The legacy fixed-target rounded-gap rule can
# choose no pad even when one complete cell rotates the earliest tap into the
# feasible window.  Example:508.1..528.6, step23 => pad508.1 once =>511.4..531.1.
namespace eval ::ot_ms_projection {}
proc ::ot_ms_projection::finite {x} {
  return [expr {[string is double -strict $x] && ![regexp -nocase {nan|inf} $x]}]
}
proc ::ot_ms_projection::select {arrivals steps window {max_rise ""}} {
  if {![dict size $arrivals] || [lsort [dict keys $arrivals]] ne [lsort [dict keys $steps]]} {
    error "OT_MSCTS_PROJECT requires identical nonempty arrival/step membership"
  }
  if {$max_rise eq ""} {set max_rise $window}
  if {![finite $window] || $window <= 0 || ![finite $max_rise] || $max_rise < 0} {
    error "OT_MSCTS_PROJECT invalid window/rise bound"
  }
  set hi -1e99;set lo 1e99
  dict for {who a} $arrivals {
    set step [dict get $steps $who]
    if {![finite $a] || ![finite $step] || $step < 8 || $step > 40} {
      error "OT_MSCTS_PROJECT needs finite arrivals and physically measured pad steps8..40ps"
    }
    set hi [expr {max($hi,$a)}];set lo [expr {min($lo,$a)}]
  }
  if {$hi-$lo <= $window} {return [dict create feasible 1 counts {} predicted $arrivals span [expr {$hi-$lo}] added_latency_ps 0.0]}
  # This is a finishing operation, not an unbounded whole-tree retargeting loop.
  if {$hi-$lo > 2*$window} {return [dict create feasible 0 reason coarse_balance_required]}
  set bounds {};set limit [expr {$hi+$max_rise}]
  dict for {who a} $arrivals {
    set step [dict get $steps $who]
    set nmax [expr {int(ceil(($limit-$a)/$step))}]
    for {set n 0} {$n <= $nmax} {incr n} {
      set v [expr {$a+$n*$step}]
      if {$v <= $limit+1e-9} {lappend bounds $v}
    }
  }
  set best {};set best_count 1e99;set best_hi 1e99;set best_span 1e99
  foreach lower [lsort -real -unique $bounds] {
    set predicted {};set counts {};set total 0;set new_lo 1e99;set new_hi -1e99
    dict for {who a} $arrivals {
      set step [dict get $steps $who]
      set n [expr {max(0,int(ceil(($lower-$a-1e-9)/$step)))}]
      set v [expr {$a+$n*$step}]
      dict set predicted $who $v
      if {$n} {dict set counts $who $n;incr total $n}
      set new_lo [expr {min($new_lo,$v)}];set new_hi [expr {max($new_hi,$v)}]
    }
    set span [expr {$new_hi-$new_lo}]
    if {$span > $window+1e-9 || $new_hi > $limit+1e-9} continue
    if {$total < $best_count || ($total == $best_count && ($new_hi < $best_hi || ($new_hi == $best_hi && $span < $best_span)))} {
      set best_count $total;set best_hi $new_hi;set best_span $span
      set best [dict create feasible 1 counts $counts predicted $predicted span $span added_latency_ps [expr {max(0.0,$new_hi-$hi)}]]
    }
  }
  if {$best eq ""} {return [dict create feasible 0 reason no_discrete_solution_within_rise_bound]}
  return $best
}
proc ::ot_ms_projection::from_stats {stats measured_steps fallback_step window} {
  set arrivals {};set steps {}
  dict for {who st} $stats {
    dict set arrivals $who [lindex $st 0]
    dict set steps $who [expr {[dict exists $measured_steps $who] ? [dict get $measured_steps $who] : $fallback_step}]
  }
  return [select $arrivals $steps $window]
}

# Shared physical pad counts must fit BOTH sign-off corner windows.  TT fitting
# already is not a reason to skip a failing FF window (mixed-edge SRAMIF case).
proc ::ot_ms_projection::select_joint {arrivals corner_steps window {max_rise ""}} {
  if {[lsort [dict keys $arrivals]] ne {FF TT} || [lsort [dict keys $corner_steps]] ne {FF TT}} {
    error "OT_MSCTS_PROJECT_JOINT requires explicit TT and FF measurements"
  }
  if {$max_rise eq ""} {set max_rise $window}
  set names [lsort [dict keys [dict get $arrivals TT]]]
  if {$names ne [lsort [dict keys [dict get $arrivals FF]]]} {error "OT_MSCTS_PROJECT_JOINT corner membership differs"}
  set old_hi {};set bounds {};set spans {}
  foreach c {TT FF} {
    set A [dict get $arrivals $c];set S [dict get $corner_steps $c]
    # Reuse the single-frame validation, including measured-cell step bounds.
    select $A $S $window $max_rise
    set hi [tcl::mathfunc::max {*}[dict values $A]]
    set lo [tcl::mathfunc::min {*}[dict values $A]]
    dict set old_hi $c $hi;dict set spans $c [expr {$hi-$lo}]
    if {$hi-$lo > 2*$window} {return [dict create feasible 0 reason coarse_balance_required corner $c]}
    set B {}
    dict for {who a} $A {
      set step [dict get $S $who]
      set nmax [expr {int(ceil(($hi+$max_rise-$a)/$step))}]
      for {set n 0} {$n <= $nmax} {incr n} {
        set v [expr {$a+$n*$step}]
        if {$v <= $hi+$max_rise+1e-9} {lappend B $v}
      }
    }
    dict set bounds $c [lsort -real -unique $B]
  }
  if {[dict get $spans TT] <= $window && [dict get $spans FF] <= $window} {
    return [dict create feasible 1 counts {} predicted $arrivals spans $spans added_latency_ps {TT 0.0 FF 0.0}]
  }
  set best {};set best_count 1e99;set best_rise 1e99
  foreach ltt [dict get $bounds TT] {
    foreach lff [dict get $bounds FF] {
      set lower [dict create TT $ltt FF $lff]
      set counts {};set total 0;set pred [dict create TT {} FF {}]
      foreach who $names {
        set n 0
        foreach c {TT FF} {
          set a [dict get $arrivals $c $who];set s [dict get $corner_steps $c $who]
          set n [expr {max($n,0,int(ceil(([dict get $lower $c]-$a-1e-9)/$s)))}]
        }
        if {$n} {dict set counts $who $n;incr total $n}
        foreach c {TT FF} {dict set pred $c $who [expr {[dict get $arrivals $c $who]+$n*[dict get $corner_steps $c $who]}]}
      }
      if {$total > $best_count} continue
      set ok 1;set new_spans {};set rises {};set rise 0.0
      foreach c {TT FF} {
        set hi [tcl::mathfunc::max {*}[dict values [dict get $pred $c]]]
        set lo [tcl::mathfunc::min {*}[dict values [dict get $pred $c]]]
        set delta [expr {max(0.0,$hi-[dict get $old_hi $c])}]
        if {$hi-$lo > $window+1e-9 || $delta > $max_rise+1e-9} {set ok 0;break}
        dict set new_spans $c [expr {$hi-$lo}];dict set rises $c $delta
        set rise [expr {max($rise,$delta)}]
      }
      if {$ok && ($total < $best_count || ($total == $best_count && $rise < $best_rise))} {
        set best_count $total;set best_rise $rise
        set best [dict create feasible 1 counts $counts predicted $pred spans $new_spans added_latency_ps $rises]
      }
    }
  }
  if {$best eq ""} {return [dict create feasible 0 reason no_joint_discrete_solution_within_rise_bound]}
  return $best
}
