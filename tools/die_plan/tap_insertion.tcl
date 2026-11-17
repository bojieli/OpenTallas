# WAVE-FLOW-R2 11-17 (COORD, FABLE-CLOSURE-STRATEGY lever 6): per-tap clock insertion after CTS, ADVISORY (never a gate, never edits the netlist).
# One line per tap, measured with tap_balance.tcl's own tb_measure (the same sink walk and arrival model as OT_TAP_RC), after the tap balance pass:
#   OT_TAP_INSERTION tap=<clock port> sinks=<n> ins_ps=<max sink arrival> skew_ps=<max - min sink arrival>
# Measured insertion, not sink counts, is what decides which oversized taps (QC 87 of 130, KV 47 of 52 over 1,650 sinks) to split in the plan.
# OT_TAP_INSERTION=0 turns it off; any error is a WARN line.
if {[info exists ::env(OT_TAP_INSERTION)] && $::env(OT_TAP_INSERTION) eq "0"} {
  puts "OT_TAP_INSERTION skipped (OT_TAP_INSERTION=0)"
} elseif {![llength [info procs tb_measure]]} {
  puts "OT_TAP_INSERTION WARN: tb_measure is not loaded (tap_balance.tcl was not sourced), no per-tap insertion"
} elseif {[catch {
  set ti_m [tb_measure 1]
  set ti_n 0
  dict for {ti_tap ti_v} $ti_m {
    puts [format "OT_TAP_INSERTION tap=%s sinks=%d ins_ps=%.1f skew_ps=%.1f" $ti_tap [lindex $ti_v 3] [lindex $ti_v 2] [expr {[lindex $ti_v 2] - [lindex $ti_v 1]}]]
    incr ti_n
  }
  puts "OT_TAP_INSERTION total taps=$ti_n"
} ti_err]} {
  puts "OT_TAP_INSERTION WARN: not printed: $ti_err"
}
unset -nocomplain ti_m ti_n ti_tap ti_v ti_err
