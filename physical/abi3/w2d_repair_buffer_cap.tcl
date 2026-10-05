# PRE_CTS / PRE_GLOBAL_ROUTE hook: raise repair_timing's buffer cap.
# With 60 ps hold uncertainty plus the 20 ps hold margin, every direct
# flop-to-flop path (e.g. the GW4 transpose's 16,384 tile cells fed straight
# from in_data_q) needs one delay cell; the default -max_buffer_percent 20
# stopped CTS with RSZ-0060 before hold closed. The area/power cost of the
# inserted hold cells is reported by the route (no timing constraint changes).
proc repair_timing_helper { args } {
  set additional_args {}
  append_env_var additional_args SETUP_SLACK_MARGIN -setup_margin 1
  append_env_var additional_args HOLD_SLACK_MARGIN -hold_margin 1
  append_env_var additional_args SETUP_MOVE_SEQUENCE -sequence 1
  append_env_var additional_args TNS_END_PERCENT -repair_tns 1
  append_env_var additional_args SKIP_PIN_SWAP -skip_pin_swap 0
  append_env_var additional_args SKIP_GATE_CLONING -skip_gate_cloning 0
  append_env_var additional_args SKIP_BUFFER_REMOVAL -skip_buffer_removal 0
  append_env_var additional_args SKIP_LAST_GASP -skip_last_gasp 0
  append_env_var additional_args SKIP_VT_SWAP -skip_vt_swap 0
  append_env_var additional_args SKIP_CRIT_VT_SWAP -skip_crit_vt_swap 0
  append_env_var additional_args MATCH_CELL_FOOTPRINT -match_cell_footprint 0
  lappend additional_args {*}$args -max_buffer_percent 60 -verbose
  log_cmd repair_timing {*}$additional_args
}
puts "OT_W2D_REPAIR_BUFFER_CAP 60%"
