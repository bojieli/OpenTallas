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
