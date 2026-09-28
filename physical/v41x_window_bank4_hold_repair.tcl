# Four-bank SRAM slice sensitivity. The default OpenROAD hold-repair cap
# stopped at 2,656 inserted buffers with remaining hold TNS. Allow more
# buffers explicitly; this is a separate physical cost point, not the baseline.
rename repair_timing_helper repair_timing_helper_default
proc repair_timing_helper { args } {
    set extra [list]
    append_env_var extra SETUP_SLACK_MARGIN -setup_margin 1
    append_env_var extra HOLD_SLACK_MARGIN -hold_margin 1
    append_env_var extra SETUP_MOVE_SEQUENCE -sequence 1
    append_env_var extra TNS_END_PERCENT -repair_tns 1
    lappend extra {*}$args -max_buffer_percent 100 -verbose
    log_cmd repair_timing {*}$extra
}
