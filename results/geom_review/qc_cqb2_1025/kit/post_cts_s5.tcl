# QC-CQB2 s5 POST_CTS: coarse tap / macro-leaf pre-balance on (RC-calibrated) placement parasitics.  The binding
# balance is the GRT-RC pass in post_grt_s5.tcl (METHODOLOGY 3.5: never placement RC).
if {[info exists ::ot_fc_dt]} { puts "OT_FCAP: dont_touch left lifted on [llength $::ot_fc_dt] flops (hold repair)" }
ot_ms_balance cts
detailed_placement
check_placement -verbose
estimate_parasitics -placement
report_clock_skew -setup
report_clock_skew -hold
