# QC-RP1 10-25 POST_CTS: F5 tap balance (<= OT_CTAP_WIN) + macro leaf latency match on placement RC, then the CTS stop gate.
# Replaces the rw100 long-branch re-buffer, tap_balance.tcl (no-op for a single-port core) and the leaf delay chains.
if {[info exists ::ot_fc_dt]} { puts "OT_FCAP: dont_touch left lifted on [llength $::ot_fc_dt] flops (hold repair)" }
estimate_parasitics -placement
source /work/core_taps_post.tcl
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_clock_skew -setup
report_clock_skew -hold
source /work/cts_gate.tcl
