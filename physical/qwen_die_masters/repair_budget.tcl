# Hold by repair (margin rule): the die-clock hold allowance (OT_IO_HOLD_SKEW) makes every pin-to-flop input path of a
# small register-boundary frame need ~100 ps of delay cells, more than repair_timing's default 20 % buffer budget
# (RSZ-0060 in s1_cst).  Raise the budget (QDM_MAX_BUF_PCT, default 300 %); nothing else changes.
if {[llength [info commands ::qdm_rth_orig]] == 0 && [llength [info commands repair_timing_helper]]} {
  rename repair_timing_helper ::qdm_rth_orig
  proc repair_timing_helper {args} {
    set pct [expr {[info exists ::env(QDM_MAX_BUF_PCT)] ? $::env(QDM_MAX_BUF_PCT) : 300}]
    ::qdm_rth_orig -max_buffer_percent $pct {*}$args
  }
}
