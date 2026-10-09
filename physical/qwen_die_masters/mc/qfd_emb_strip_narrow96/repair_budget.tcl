# Hold by repair (margin rule): the die-clock hold allowance (OT_IO_HOLD_SKEW) makes every pin-to-flop input path of a
# small register-boundary frame need ~100 ps of delay cells, more than repair_timing's default 20 % buffer budget
# (RSZ-0060 in s1_cst).  Raise the budget (QDM_MAX_BUF_PCT, default 100 %, the tool maximum); nothing else changes.
if {[llength [info commands ::qdm_rth_orig]] == 0 && [llength [info commands repair_timing_helper]]} {
  rename repair_timing_helper ::qdm_rth_orig
  proc repair_timing_helper {args} {
    set pct [expr {[info exists ::env(QDM_MAX_BUF_PCT)] ? $::env(QDM_MAX_BUF_PCT) : 100}]
    # the budget is a percentage of the CURRENT instance count: a pass that runs out (RSZ-0060) is followed by
    # another on the grown design, up to QDM_REPAIR_PASSES (default 6), so hold is closed by repair, not waived
    set n [expr {[info exists ::env(QDM_REPAIR_PASSES)] ? $::env(QDM_REPAIR_PASSES) : 6}]
    for {set i 1} {$i <= $n} {incr i} {
      if {![catch {::qdm_rth_orig -max_buffer_percent $pct {*}$args} msg]} { return }
      if {![string match *RSZ-0060* $msg]} { error $msg }
      puts "QDM repair pass $i ran out of buffer budget; continuing on the grown design"
    }
    error "QDM: repair_timing still out of buffer budget after $n passes"
  }
}
