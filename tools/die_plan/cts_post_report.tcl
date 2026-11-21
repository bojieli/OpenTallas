# CTS-POST-RPT-1 (S81-GEOM-OPUS 11-19, every die): ORFS cts.tcl writes 4_cts_final.rpt ("cts final" metrics) BEFORE it
# sources POST_CTS_TCL, so that report and its cts__timing metrics price the clock before tap_balance pads the tap
# trees.  S81 col_h10_r1 pv6a7ae122: the report shows g_chunk[13].rq on clk_t19 at 66 ps against wr on clk_t12 at
# 323 ps (hold -207.56) while the written DB has the clk_t19_tb0_d* pad chain and both taps balanced at 436 / 437 ps;
# col_h9_r0_p6 pvb38a9d6c the same (t9 449 / t13 433).  This step, sourced LAST by cts_post.tcl, re-reports on the
# netlist that is written to 4_1_cts.odb: one log line OT_CTS_POST_TIMING and <REPORTS_DIR>/4_cts_post_hook.rpt.
# Read these, not 4_cts_final.rpt, for CTS-stage setup / hold.  Report only: no netlist change.
if {[catch {
  estimate_parasitics -placement
  set cpr_sw [sta::worst_slack -max]; set cpr_st [sta::total_negative_slack -max]
  set cpr_hw [sta::worst_slack -min]; set cpr_ht [sta::total_negative_slack -min]
  puts [format "OT_CTS_POST_TIMING setup_ws %.2f setup_tns %.1f hold_ws %.2f hold_tns %.1f (after POST_CTS hooks; 4_cts_final.rpt is pre-hook)" $cpr_sw $cpr_st $cpr_hw $cpr_ht]
  if {[info exists ::env(REPORTS_DIR)]} {
    set cpr_f [file join $::env(REPORTS_DIR) 4_cts_post_hook.rpt]
    sta::redirect_file_begin $cpr_f
    puts [format "setup_ws %.2f setup_tns %.1f hold_ws %.2f hold_tns %.1f" $cpr_sw $cpr_st $cpr_hw $cpr_ht]
    report_checks -path_delay max -group_path_count 5 -fields {slew cap fanout} -digits 2
    report_checks -path_delay min -group_path_count 5 -fields {slew cap fanout} -digits 2
    sta::redirect_file_end
  }
} cpr_err]} { puts "OT_CTS_POST_TIMING WARN report failed: $cpr_err" }
# TAP-GRID-2130 (FABLE-CLOSURE-STRATEGY 21:30 lever 2, every die): make the POST-hook read the ONE canonical CTS read.  ORFS
# report_metrics is re-run here, on the netlist that is written to 4_1_cts.odb, so 4_cts_final.rpt and the cts__timing__*
# metrics of 4_1_cts.json (the last value of a key wins) are post-hook for every consumer (noprog watchdog, failure classes,
# root_entry_scan, stuckscan, fleet_viz).  The pre-hook report is kept as 4_cts_final_prehook.rpt for forensics only (no clock
# verdict from it).  The rewritten report carries the line OT_CTS_FINAL_POSTHOOK; readers of older kits use cts_read.py.
# OT_CTS_FINAL_POSTHOOK=0 (config.mk) = off (old files).  Report only: no netlist change.
if {(![info exists ::env(OT_CTS_FINAL_POSTHOOK)] || $::env(OT_CTS_FINAL_POSTHOOK) ne "0") && [llength [info procs ::report_metrics]]
    && [info exists ::env(REPORTS_DIR)]} {
  if {[catch {
    set cpr_fin [file join $::env(REPORTS_DIR) 4_cts_final.rpt]
    if {[file exists $cpr_fin]} { file rename -force $cpr_fin [file join $::env(REPORTS_DIR) 4_cts_final_prehook.rpt] }
    ::report_metrics 4 "cts final"
    set cpr_fh [open $cpr_fin a]
    puts $cpr_fh "\nOT_CTS_FINAL_POSTHOOK report_metrics re-run after the POST_CTS hooks (pre-hook copy: 4_cts_final_prehook.rpt)"
    close $cpr_fh
    puts "OT_CTS_FINAL_POSTHOOK 4_cts_final.rpt + cts__timing metrics rewritten after the POST_CTS hooks (pre-hook copy 4_cts_final_prehook.rpt)"
  } cpr_err2]} { puts "OT_CTS_FINAL_POSTHOOK WARN rewrite failed: $cpr_err2" }
}
