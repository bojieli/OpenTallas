# Diagnostic only: preserve the real CTS tree before repair can fail without an ODB.
# Called as PRE_CTS by the unchanged ORFS cts.tcl in a separate work directory.
# All clocks, IO delays, corner libraries, and macro capture arcs stay unchanged.
rename repair_timing_helper r5a_original_repair_timing_helper
proc repair_timing_helper {} {
    set_propagated_clock [all_clocks]
    puts "R5A_DIAGNOSTIC_ONLY placement-estimated RC, before setup/hold repair"
    foreach corner $::env(CORNERS) {
        foreach delay {min max} {
            report_checks -corner $corner -path_delay $delay -group_path_count 5 \
                -format full_clock_expanded -fields {slew cap fanout input net} -digits 4 \
                > $::env(RESULTS_DIR)/r5a_${corner}_${delay}.rpt
            report_checks -corner $corner -path_delay $delay \
                -to [get_pins {on.u_ids.wbin\[0\]$_DFF_PN0_/D}] \
                -group_path_count 1 -format full_clock_expanded \
                -fields {slew cap fanout input net} -digits 4 \
                > $::env(RESULTS_DIR)/r5a_ids_${corner}_${delay}.rpt
        }
    }
    orfs_write_db $::env(RESULTS_DIR)/r5a_pre_repair.odb
    orfs_write_sdc $::env(RESULTS_DIR)/r5a_pre_repair.sdc
    puts "R5A_CTS_CAPTURE_COMPLETE (diagnostic, not route/signoff)"
    exit 0
}
